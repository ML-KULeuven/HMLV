from collections import defaultdict

import numpy as np
import pandas as pd
from tqdm import tqdm

from utils.utility import create_folders


class CPE:
    def __init__(self, model, oracle, objectives, preferred, nadir_optimal_results, output_location='./default',
                 time_eval=10, lr=0.1, max_data=50, disjunctive=False, normalization='base',
                 diversification='base', c_ucb=2):
        self.model = model
        self.oracle = oracle
        self.max_data = max_data
        self.objectives = objectives
        self.output_location = output_location
        self.labelled = 1
        self.time_eval = time_eval
        self.lr = lr
        self.preferred = preferred
        self.nadir_optimal_results = nadir_optimal_results
        self.weights_learned = {obj:1 for obj in objectives}
        self.regret_dataset = []
        self.disjunctive = disjunctive
        self.normalization = normalization
        self.diversification = diversification
        self.c_ucb = c_ucb
        self.first_solution_hint = None
        create_folders(self.output_location)

    def start(self):
        # Progress bar for labelling process
        self.dataset = []

        with tqdm(total=self.max_data, desc="Labelling progress") as pbar:
            while self.labelled <= self.max_data:
                query_for_oracle_normalized, obj_1_raw, obj_2_raw, time_1, time_2, regret = self.acquisition_function()  # Select queries for labelling
                picked, _, val_1, _, val_2, obj_preferred_idx = self.oracle.label([obj_1_raw, obj_2_raw])

                user_feedback = '' # New variable to store 'indiff', 'correct', 'wrong'
                if picked == -1:
                    label = 'Draw'
                    user_feedback = 'indiff'
                else:
                    label = picked
                    if picked == obj_preferred_idx:
                        user_feedback = 'correct'
                    else:
                        user_feedback = 'wrong'
                    self.train(query_for_oracle_normalized[picked], query_for_oracle_normalized[1 - picked])

                self.dataset.append([self.labelled, obj_1_raw, obj_2_raw, label, user_feedback, time_1, time_2, regret])
                df_dataset = pd.DataFrame(self.dataset, columns=['iter', 'obj 1',
                                                            'obj 2', 'picked', 'user_feedback',
                                                            'time 1', 'time 2', 'Regret'])
                df_dataset.to_csv(f'{self.output_location}' + f'/dataset.csv')
                self.labelled += 1


                # Periodically evaluate regret and performance
                if self.labelled % self.time_eval == 0:
                    self.evaluate()
                pbar.update(1)
        return self.weights_learned

    def acquisition_function(self):
        if self.normalization=='base':
            time_1, _, image_1_raw = self.model.solve(self.weights_learned, timeout=30,
                                                      nadir_points=self.nadir_optimal_results,
                                                      solution_hint=False)

        elif self.normalization=='custom' or self.normalization=='local':
            time_1, _, image_1_raw = self.model.solve(self.weights_learned, timeout=30,
                                                      solution_hint=False)

        # self.first_solution_hint = self.model.get_variable_values()

        if self.normalization == 'custom':
            for obj in image_1_raw:
                self.nadir_optimal_results[obj]['max'] = image_1_raw[obj]

        regret = (
                sum(
                    self.oracle.dict_feature_weights[obj]
                    * (image_1_raw[obj] - self.preferred[obj])
                    for obj in image_1_raw
                )
                /
                sum(
                    self.oracle.dict_feature_weights[obj]
                    * self.preferred[obj]
                    for obj in image_1_raw
                )
        )
        if self.normalization!='local':
            time_2, _, image_2_raw = self.model.solve(self.weights_learned, image_1_raw,self.disjunctive,
                                                      self.labelled,timeout=30, nadir_points=self.nadir_optimal_results,
                                                      diversification = self.diversification, trade_offs = self.dataset,
                                                      c_ucb = self.c_ucb, solution_hint=False)
        else:
            time_2, _, image_2_raw = self.model.solve(self.weights_learned, image_1_raw,self.disjunctive,
                                                      self.labelled,timeout=30, nadir_points=None,
                                                      diversification = self.diversification, trade_offs = self.dataset,
                                                      c_ucb = self.c_ucb, solution_hint=False)

        print('\n')
        print(image_1_raw)
        print(image_2_raw)



        if self.normalization == 'custom':
            for obj in image_1_raw:
                self.nadir_optimal_results[obj]['max'] = max(image_1_raw[obj],image_2_raw[obj])

        image_1_normalized = image_1_raw.copy()
        image_2_normalized = image_2_raw.copy()

        for obj_name in image_1_normalized:
            min_v = self.nadir_optimal_results[obj_name]['min']
            max_v = self.nadir_optimal_results[obj_name]['max']
            denom = max_v - min_v
            if denom == 0:
                denom = 1

            image_1_normalized[obj_name] = (image_1_normalized[obj_name] - self.nadir_optimal_results[obj_name]['min']) / denom
            image_2_normalized[obj_name] = (image_2_normalized[obj_name] - self.nadir_optimal_results[obj_name]['min']) / denom

        return [image_1_normalized, image_2_normalized], image_1_raw, image_2_raw, time_1, time_2, regret

    def train(self, preferred, not_preferred):
        difference = defaultdict(int)
        for key in self.objectives:
            difference[key] = not_preferred[key] - preferred[key]
            self.weights_learned[key] = max(1e-4, self.weights_learned[key] + self.lr * np.clip(difference[key], -1000, 1000))
        # max_val = max(self.weights_learned.values())
        # self.weights_learned = {
        #     k: v / max_val for k, v in self.weights_learned.items()
        # }
        print(self.weights_learned)

    def evaluate(self):
        if self.normalization=='base':
            _, _, objs = self.model.solve(self.weights_learned, timeout=300,
                                                      nadir_points=self.nadir_optimal_results)
        elif self.normalization=='custom' or self.normalization=='local':
            _, _, objs = self.model.solve(self.weights_learned, timeout=300)

        regret = (
                sum(
                    self.oracle.dict_feature_weights[obj]
                    * (objs[obj] - self.preferred[obj])
                    for obj in objs
                )
                /
                sum(
                    self.oracle.dict_feature_weights[obj]
                    * self.preferred[obj]
                    for obj in objs
                )
        )
        self.regret_dataset.append([self.labelled, self.weights_learned.copy(), regret, self.preferred, objs]) # .copy() to avoid modifying dict in place
        pd.DataFrame(self.regret_dataset, columns=['iter', 'weights_learned', 'regret', 'preferred_solution', 'computed_solution']).to_csv(f'{self.output_location}' + f'/regret.csv', index=False)


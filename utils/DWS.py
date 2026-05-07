import time
import pandas as pd
from utils.utility import create_folders


from cpmpy.solvers.solver_interface import ExitStatus

class DWS:
    def __init__(self, model, oracle, objectives, preferred, nadir_optimal_results,
                 output_location='./default', time_eval=10, timeout_query=60,
                 ub=10,lb=0.1,alpha=1, max_data=60, normalization='base'):
        self.model = model
        self.oracle = oracle
        self.weights_learned = {obj: 1 for obj in objectives}
        self.nadir_optimal_results = nadir_optimal_results
        self.timeout_query = timeout_query
        self.ub = ub
        self.lb = lb
        self.alpha = alpha
        self.time_eval = time_eval
        self.labelled = 1
        self.preferred = preferred
        self.regret_dataset = []
        self.solve_history = []
        self.output_location = output_location
        self.max_data = max_data
        self.normalization = normalization
        create_folders(self.output_location)

    def record_solve(self, weights, bounds, results, solve_time):
        regret = self._compute_regret(results)
        self.solve_history.append({
            'iter': self.labelled,
            'weights': weights.copy(),
            'bounds': bounds.copy() if bounds is not None else None,
            'results': results.copy(),
            'regret': regret,
            'solve_time': solve_time
        })
        pd.DataFrame(self.solve_history).to_csv(f'{self.output_location}/solve_history.csv', index=False)



    def _compute_regret(self, results):
        if results is None:
            return None
        
        numerator = sum(
            self.oracle.dict_feature_weights[obj]
            * (results[obj] - self.preferred[obj])
            for obj in results
        )
        denominator = sum(
            self.oracle.dict_feature_weights[obj]
            * self.preferred[obj]
            for obj in results
        )
        return numerator / denominator if denominator != 0 else 0

    def start(self):
        if self.normalization == 'base':
            solve_time, status, image_1_raw = self.model.solve(self.weights_learned, timeout=30,
                                                      nadir_points=self.nadir_optimal_results)
        elif self.normalization == 'custom':
            solve_time, status, image_1_raw = self.model.solve(self.weights_learned, timeout=30)
            for obj in image_1_raw:
                self.nadir_optimal_results[obj]['max'] = image_1_raw[obj]
        
        if status == ExitStatus.UNSATISFIABLE:
            print("Initial solve is UNSAT. This should not happen with base weights.")
            return

        print(f"Initial solve took: {solve_time:.2f}s")
        self.record_solve(self.weights_learned, None, image_1_raw, solve_time)

        while self.labelled <= self.max_data:
            bounds = self.oracle.query_bounds(image_1_raw)
            self.record_solve(self.weights_learned, bounds, image_1_raw, 0) # No solve call here, just recording bounds
            
            print(f"\n{'='*30}")
            print(f"Iteration: {self.labelled}")
            print(f"Oracle Preferred Solution: {self.preferred}")
            print(f"Current Weights:           {self.weights_learned}")
            print(f"Current Solution:          {image_1_raw}")
            print(f"Oracle Bounds:             {bounds}")
            print(f"{'='*30}")

            time_one_query = 0
            inner_loop_count = 0
            inner_weights = self.weights_learned.copy()
            while (not self.satisfied(image_1_raw,bounds)
                   and time_one_query < self.timeout_query
                   and inner_loop_count < 20):
                inner_loop_count += 1
                start_time = time.time()
                self.update_weights(image_1_raw, bounds, self.nadir_optimal_results, inner_weights)
                
                if self.normalization == 'base':
                    solve_time, status, image_1_raw = self.model.solve(inner_weights, timeout=30,
                                                              nadir_points=self.nadir_optimal_results)
                elif self.normalization == 'custom':
                    solve_time, status, image_1_raw = self.model.solve(inner_weights, timeout=30)
                    for obj in image_1_raw:
                        self.nadir_optimal_results[obj]['max'] = image_1_raw[obj]

                if status == ExitStatus.UNSATISFIABLE:
                    print(f"  [Inner {inner_loop_count}] UNSAT detected. Re-querying oracle for new bounds...")
                    bounds = self.oracle.query_bounds(image_1_raw)
                    print(f"  [Inner {inner_loop_count}] New Oracle Bounds: {bounds}")
                    self.record_solve(inner_weights, bounds, image_1_raw, solve_time)
                    # We continue the loop with new bounds but same weights
                    time_one_query = time_one_query + time.time() - start_time
                    continue

                print(f"  [Inner {inner_loop_count}] Weights updated: {inner_weights}. Solve took: {solve_time:.2f}s")
                print(f"  [Inner {inner_loop_count}] New Solution: {image_1_raw}")
                self.record_solve(inner_weights, bounds, image_1_raw, solve_time)
                time_one_query = time_one_query + time.time() - start_time
            
            if self.satisfied(image_1_raw, bounds):
                self.weights_learned = inner_weights.copy()

            if self.labelled % self.time_eval == 0:
                self.evaluate()
            self.labelled += 1

    def satisfied(self,image_1_raw,bounds):
        for obj in image_1_raw:
            if bounds.get(obj) is not None:
                if image_1_raw[obj]-bounds[obj] > 0:
                    return False
        return True


    def update_weights(self,image_1_raw, bounds, normalization, weights):
        for obj in image_1_raw:
            if bounds[obj] is not None:
                if image_1_raw[obj]-bounds[obj] > 0:
                    denom = normalization[obj]['max'] - normalization[obj]['min']
                    if denom == 0:
                        denom = 1
                        
                    new_weights = (
                            weights[obj] *
                            min(
                                [
                                    max(
                                        [
                                            1 + self.alpha * (
                                                    (image_1_raw[obj] - bounds[obj]) /
                                                    denom
                                            ),
                                            self.lb
                                        ]
                                    ),
                                    self.ub
                                ]
                            )
                    )
                    weights[obj] = new_weights


    def evaluate(self):
        if self.normalization == 'base':
            solve_time, status, objs = self.model.solve(self.weights_learned, timeout=300, solver='ortools',
                                         nadir_points=self.nadir_optimal_results)
        elif self.normalization == 'custom':
            solve_time, status, objs = self.model.solve(self.weights_learned, timeout=300, solver='ortools')

        if status == ExitStatus.UNSATISFIABLE:
            print(f"Warning: Evaluation solve was UNSAT at iteration {self.labelled}. Skipping regret calculation.")
            return
        regret = self._compute_regret(objs)
        self.regret_dataset.append([self.labelled, self.weights_learned.copy(), regret, self.preferred,
                                    objs, solve_time])  # .copy() to avoid modifying dict in place
        pd.DataFrame(self.regret_dataset,
                     columns=['iter', 'weights_learned', 'regret', 'preferred_solution', 'computed_solution', 'solve_time']).to_csv(
            f'{self.output_location}' + f'/regret.csv', index=False)
















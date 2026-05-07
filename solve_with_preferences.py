import pandas as pd
import json
from utils.jobshop_model_final import FJTransportProblemFinal
import time

def solve_problem(json_file, weights, timeout, nadir_points=None):
    problem = FJTransportProblemFinal(custom_bound=False, json_file=json_file, symmetry_breaking=False)
    problem.make_model()
    objectives = ['makespan', 'workstations', 'employees', 'robots', 'employee_time']
    weights_dict = dict(zip(objectives, weights))

    # Pass nadir_points if provided
    elapsed, status, objs = problem.solve(objectives=weights_dict, timeout=timeout, nadir_points=nadir_points)
    return status, objs

def main():
    user_preferences = pd.read_csv('data/user_preferences.csv')

    training_results_1 = []
    training_results_2 = []

    timeout = 300 # 5 minutes timeout for each solve

    for index, row in user_preferences.iterrows():
        weights = row.values
        
        print(f"Solving for user preference {index}...")

        # Solve for training data
        print("  Solving for training data...")
        start_time = time.time()
        train_status, train_objs = solve_problem('data/data_training_2.json', weights, timeout)
        train_time = time.time() - start_time
        print(f"    - Status: {train_status}, Time: {train_time:.2f}s")
        training_results_1.append({
            'weights': weights.tolist(),
            'status': train_status,
            'objectives': train_objs
        })

        # print("  Solving for training data...")
        # start_time = time.time()
        # train_status, train_objs = solve_problem('data/data_training_3.json', weights, timeout)
        # train_time = time.time() - start_time
        # print(f"    - Status: {train_status}, Time: {train_time:.2f}s")
        # training_results_2.append({
        #     'weights': weights.tolist(),
        #     'status': train_status,
        #     'objectives': train_objs
        # })

        # Solve for test data (small)
        # print("  Solving for small test data...")
        # start_time = time.time()
        # test_small_status, test_small_objs = solve_problem('data/data_test_small.json', weights, timeout)
        # test_small_time = time.time() - start_time
        # print(f"    - Status: {test_small_status}, Time: {test_small_time:.2f}s")
        # test_small_results.append({
        #     'weights': weights.tolist(),
        #     'status': "SKIPPED", # Correctly assign "SKIPPED" status
        #     'objectives': {}
        # })

    pd.DataFrame(training_results_1).to_csv('data/solution_training_2.csv', index=False)
    # pd.DataFrame(training_results_2).to_csv('data/solution_training_3.csv', index=False)
    # pd.DataFrame(test_small_results).to_csv('data/solution_test_small.csv', index=False)


if __name__ == "__main__":
    main()

import json
import numpy as np
import pandas as pd
import os
from datetime import datetime

from metrics import compare_trajectories
from utils import (
    normalize_string,
    create_diff_dataframe,
    extract_agent_tool_sequence,
    count_turns_all,
    calculate_average_latency,
    count_errors,
    get_customer_trajectory_data,
    extract_ground_truth_trajectory,
    aggregation_metrics,
    sort_dataframe)


class EvaluationProcessor:
    """Process evaluation data and compute metrics."""
    
    def __init__(self, data_file="evaluation_data.json"):
        """Load the evaluation data."""
        with open(data_file, 'r') as f:
            self.data = json.load(f)
        self.experiments = self.data['data']
        
        # filter to experiments that have complete data (customer data, traj data, gt)
        self.evaluable_experiments = [
            exp for exp in self.experiments 
            if (exp.get('customer_data') and len(exp.get('customer_data', [])) > 0 and
                exp.get('trajectory_data') and len(exp.get('trajectory_data', [])) > 0 and
                exp.get('ground_truth') and self._has_complete_ground_truth(exp))
        ]
        print(f"Loaded {len(self.experiments)} experiments, {len(self.evaluable_experiments)} evaluable")
    
    def _has_complete_ground_truth(self, experiment):
        """Check if experiment has complete ground truth data for all customers."""
        ground_truth = experiment.get('ground_truth', {})
        if not ground_truth:
            return False
        
        customer_data_list = experiment.get('customer_data', [])
        for customer_data in customer_data_list:
            customer_id = customer_data.get('customer_id')
            if not customer_id or str(customer_id) not in ground_truth:
                return False
            
            customer_gt = ground_truth[str(customer_id)]
            if not customer_gt or not customer_gt.get('traxgen'):
                return False
        
        return True

    def process_single_customer_in_experiment(self, experiment, customer_data):
        """Process evaluation metrics for a single customer within an experiment."""
        customer_id = customer_data.get('customer_id')
        if not customer_id:
            return None
        
        # get customer's trajectory data
        trajectory_data = experiment.get('trajectory_data', [])
        customer_trajectory = get_customer_trajectory_data(trajectory_data, customer_id)
        
        if not customer_trajectory:
            return None
        
        # get generated sequence
        data = customer_trajectory.get('data', [])
        if not data:
            return None
            
        generated_sequence = extract_agent_tool_sequence(data)
        generated_sequence_normalized = [normalize_string(item) for item in generated_sequence]
        
        # get ground truth
        ground_truth = experiment.get('ground_truth', {})
        ground_truth_trajectory = extract_ground_truth_trajectory(ground_truth, customer_id)
        ground_truth_normalized = [normalize_string(item) for item in ground_truth_trajectory]
        
        if not ground_truth_normalized:
            return None
        
        # calculate trajectory metrics
        trajectory_metrics = compare_trajectories(generated_sequence_normalized, ground_truth_normalized)
        
        # calculate performance metrics
        turns_all = count_turns_all(data, fulfillment=False)
        turns_fulfillment = count_turns_all(data, fulfillment=True)
        avg_latency_all = calculate_average_latency(data, fulfillment=False)
        avg_latency_fulfillment = calculate_average_latency(data, fulfillment=True)
        error_count = count_errors(data)
        
        # map intent to domain
        intent_to_domain = {
            'update_address': 'banking',
            'withdraw_retirement_funds': 'banking', 
            'book_flight': 'flights',
            'cancel_flight': 'flights',
            'process_payment': 'hospital'
        }
        
        domain = intent_to_domain.get(experiment['intent'], 'unknown')
        
        return {
            'customer_id': str(customer_id),
            'domain': domain,
            'intent': experiment['intent'],
            'model': experiment['model'],
            'experiment_type': experiment['method'],
            # All trajectory metrics from compare_trajectories
            'exact_match': trajectory_metrics["exact_match"],
            'agent_match_%_any_order': trajectory_metrics["agent_match_percentage_any_order"],
            'agent_match_%_order': trajectory_metrics["agent_match_percentage_order"],
            'lcs_tools': trajectory_metrics["lcs_tools"],
            'tool_precision': trajectory_metrics["tool_precision"],
            'tool_recall': trajectory_metrics["tool_recall"],
            'tool_f1': trajectory_metrics["tool_f1_score"],
            'fulfill_tool_precision': trajectory_metrics["fulfillment_tool_precision"],
            'fulfill_tool_recall': trajectory_metrics["fulfillment_tool_recall"],
            'fulfill_tool_f1': trajectory_metrics["fulfillment_tool_f1_score"],
            'param_match_%': trajectory_metrics["param_match_percentage"],
            # Performance metrics
            'turns_all_agents': turns_all,
            'turns_fulfill_agents': turns_fulfillment,
            'average_latency': avg_latency_all,
            'fulfill_agent_latency': avg_latency_fulfillment,
            'error_count': error_count,
        }

    def process_single_experiment(self, experiment):
        """Process all customers in a single experiment."""
        customer_data_list = experiment.get('customer_data', [])
        results = []
        
        for customer_data in customer_data_list:
            result = self.process_single_customer_in_experiment(experiment, customer_data)
            if result:
                results.append(result)
        
        return results

    def evaluate_all_experiments(self):
        """Run evaluation on all evaluable experiments."""
        print(f"Starting evaluation of {len(self.evaluable_experiments)} experiments...")
        
        all_results = []
        for i, experiment in enumerate(self.evaluable_experiments, 1):
            print(f"Processing experiment {i}/{len(self.evaluable_experiments)}: {experiment['intent']} - {experiment['model']}")
            experiment_results = self.process_single_experiment(experiment)
            all_results.extend(experiment_results)
        
        print(f"Evaluation complete! Processed {len(all_results)} total customer evaluations")
        return all_results

    def create_summary_dataframes(self, results):
        """Create summary DataFrames from evaluation results."""
        if not results:
            return {}
        
        client_df_clean = pd.DataFrame(results)

        intent_order = ['update_address', 'withdraw_retirement_funds', 'book_flight', 'cancel_flight', 'process_payment']
        experiment_type_order = ['react', 'no_parallel', 'parallel']
        model_order = ['llama', 'gpt', 'sonnet']

        # Create sequences comparison DataFrame
        sequences_df = self.create_sequences_comparison_dataframe(results)

        # experiment summary
        experiment_summary = client_df_clean.groupby(['experiment_type']).agg(aggregation_metrics).round(2).reset_index()
        experiment_summary = sort_dataframe(experiment_summary, ['experiment_type_cat'])
        
        # intent x experiment summary
        intent_experiment_summary = client_df_clean.groupby(['intent', 'experiment_type']).agg(aggregation_metrics).round(2).reset_index()
        intent_experiment_summary = sort_dataframe(intent_experiment_summary, ['intent_cat', 'experiment_type_cat'])
        
        # intent x model summary
        intent_model_summary = client_df_clean.groupby(['intent', 'model']).agg(aggregation_metrics).round(2).reset_index()
        intent_model_summary = sort_dataframe(intent_model_summary, ['intent_cat', 'model_cat'])
        
        # intent x experiment x model summary
        intent_model_experiment_summary = client_df_clean.groupby(['intent', 'model', 'experiment_type']).agg(aggregation_metrics).round(2).reset_index()
        intent_model_experiment_summary = sort_dataframe(intent_model_experiment_summary, ['intent_cat', 'model_cat', 'experiment_type_cat'])
        
        # difference analysis
        diff_df = create_diff_dataframe(client_df_clean)
        
        return {
            'client_level': client_df_clean,
            'experiment_level': experiment_summary,
            'intent_experiment_level': intent_experiment_summary,
            'intent_model_level': intent_model_summary,
            'intent_model_experiment_level': intent_model_experiment_summary,
            'differences': diff_df,
            'sequences_comparison': sequences_df
        }

    def create_sequences_comparison_dataframe(self, results):
        """Create sequences comparison DataFrame with all sequence data and metrics."""
        if not results:
            return pd.DataFrame()
        
        sequences_rows = []
        
        for result in results:
            customer_id = result['customer_id']
            experiment = next((exp for exp in self.evaluable_experiments 
                             if exp['intent'] == result['intent'] and 
                                exp['model'] == result['model'] and 
                                exp['method'] == result['experiment_type']), None)
            
            if experiment is None:
                continue
            
            # Get the actual sequences
            trajectory_data = experiment.get('trajectory_data', [])
            customer_trajectory = get_customer_trajectory_data(trajectory_data, customer_id)
            
            if not customer_trajectory:
                continue
            
            data = customer_trajectory.get('data', [])
            if not data:
                continue
                
            generated_sequence = extract_agent_tool_sequence(data)
            
            # Get ground truth
            ground_truth = experiment.get('ground_truth', {})
            ground_truth_trajectory = extract_ground_truth_trajectory(ground_truth, customer_id)
            
            sequences_rows.append({
                'customer_id': customer_id,
                'model': result['model'],
                'method': result['experiment_type'],
                'intent': result['intent'],
                'generated_sequence': generated_sequence,
                'ground_truth_sequence': ground_truth_trajectory,
                'exact_match': result['exact_match'],
                'agent_match_%_any_order': result['agent_match_%_any_order'],
                'agent_match_%_order': result['agent_match_%_order'],
                'lcs_tools': result['lcs_tools'],
                'tool_precision': result['tool_precision'],
                'tool_recall': result['tool_recall'],
                'tool_f1': result['tool_f1'],
                'fulfill_tool_precision': result['fulfill_tool_precision'],
                'fulfill_tool_recall': result['fulfill_tool_recall'],
                'fulfill_tool_f1': result['fulfill_tool_f1'],
                'param_match_%': result['param_match_%'],
                'turns_all_agents': result['turns_all_agents'],
                'turns_fulfill_agents': result['turns_fulfill_agents'],
                'average_latency': result['average_latency'],
                'fulfill_agent_latency': result['fulfill_agent_latency'],
                'error_count': result['error_count'],
                'generated_length': len(generated_sequence),
                'ground_truth_length': len(ground_truth_trajectory),
                'length_difference': abs(len(generated_sequence) - len(ground_truth_trajectory))
            })
        
        return pd.DataFrame(sequences_rows)

    def save_results(self, results, output_prefix="evaluation"):
        """Save evaluation results to CSV files."""
        if not results:
            print("No results to save")
            return
        
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        
        summaries = self.create_summary_dataframes(results)
        
        files_saved = []
        for level, df in summaries.items():
            if df is not None and not df.empty:
                if level == 'sequences_comparison':
                    filename = "all_sequences_comparison.csv"
                else:
                    filename = f"{output_prefix}_{level}.csv"
                filepath = os.path.join(output_dir, filename)
                df.to_csv(filepath, index=False)
                files_saved.append(filepath)
                print(f"Saved {filepath} ({len(df)} records)")
        
        print(f"All results saved! Files: {', '.join(files_saved)}")


def main():
    """Main function to run the evaluation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run evaluation on complete evaluation data")
    parser.add_argument("--data_file", default="evaluation_data.json", 
                       help="JSON file containing complete evaluation data")
    parser.add_argument("--output_prefix", default="evaluation", 
                       help="Prefix for output files")
    
    args = parser.parse_args()
    
    try:
        processor = EvaluationProcessor(args.data_file)
        results = processor.evaluate_all_experiments()
        processor.save_results(results, args.output_prefix)
        print("Evaluation completed successfully!")
        
    except FileNotFoundError:
        print(f"Error: Could not find data file {args.data_file}")
        print("Make sure to run evaluation_data_collector.py first to generate the data file")
    except Exception as e:
        print(f"Error during evaluation: {e}")
        raise


if __name__ == "__main__":
    main() 
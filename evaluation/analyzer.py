import pandas as pd
import json
from typing import Dict, Any, Tuple
from pathlib import Path
import matplotlib.pyplot as plt
import logging
from utils import sort_dataframe, load_json_data

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_usage_data(data: Dict[str, Any]) -> Tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    for exp in data.get('data', []):
        model = exp.get('model')
        method = exp.get('method')
        intent = exp.get('intent')
        usage_list = exp.get('usage_data', [])
        if not usage_list:
            continue
        for usage_file in usage_list:
            filename = usage_file.get('filename')
            entries = usage_file.get('data', [])
            for entry in entries:
                rows.append({
                    'model': model,
                    'method': method,
                    'intent': intent,
                    'usage_filename': filename,
                    'agent': entry.get('agent'),
                    'type': entry.get('type'),
                    'prompt_tokens': entry.get('prompt_tokens', 0),
                    'completion_tokens': entry.get('completion_tokens', 0),
                    'total_tokens': entry.get('total_tokens', 0),
                })
    if not rows:
        logger.warning("No usage data found!")
        return pd.DataFrame(), pd.DataFrame()
    df = pd.DataFrame(rows)
    logger.info(f"Extracted {len(df)} usage entries")
    
    # full summary (by intent, model, method, agent, type)
    full_summary = (
        df.groupby(['intent', 'model', 'method', 'agent', 'type'], dropna=False)
        .agg({
            'prompt_tokens': 'mean',
            'completion_tokens': 'mean',
            'total_tokens': 'mean'
        })
        .reset_index()
        .rename(columns={
            'prompt_tokens': 'avg_prompt_tokens',
            'completion_tokens': 'avg_completion_tokens',
            'total_tokens': 'avg_total_tokens'
        })
    )
    # count
    count_summary = (
        df.groupby(['intent', 'model', 'method', 'agent', 'type'], dropna=False)
        .size().reset_index(name='count_entries')
    )
    full_summary = full_summary.merge(count_summary, on=['intent', 'model', 'method', 'agent', 'type'])
    for col in ['avg_prompt_tokens', 'avg_completion_tokens', 'avg_total_tokens']:
        full_summary[col] = full_summary[col].round(2)
    
    # aggreagted summary (by intent, model, method only)
    aggregated_summary = (
        full_summary.groupby(['intent', 'model', 'method'])
        .agg({
            'avg_total_tokens': 'mean',
        })
        .reset_index()
        .round(2)
    )
        
    return full_summary, aggregated_summary

def create_latency_plot(metrics_csv: str, output_path: str):
    df = pd.read_csv(metrics_csv)
    col_map = {
        'agent_match_%_any_order': 'avg_tool_f1_score',
        'average_latency': 'avg_average_latency',
    }
    df_renamed = df.rename(columns=col_map)
    models = sorted(df_renamed['model'].unique())
    fig, axes = plt.subplots(len(models), 1, figsize=(7, 4 * len(models)), sharex=True)
    if len(models) == 1:
        axes = [axes]
    for ax, model in zip(axes, models):
        sub = df_renamed[df_renamed['model'] == model]
        for method, grp in sub.groupby('experiment_type'):
            ax.scatter(grp['avg_average_latency'],
                      grp['avg_tool_f1_score'],
                      label=method,
                      alpha=0.7,
                      s=40)
        ax.set_title(f"Model: {model}")
        ax.set_xlabel("Avg Latency (s)")
        ax.set_ylabel("Tool-F1")
        ax.grid(True)
        ax.legend()
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    logger.info(f"Latency plot saved to {output_path}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Extract usage stats and create latency vs tool-F1 plot from evaluation data.")
    parser.add_argument('--data_file', default='evaluation_data.json', help='Path to evaluation_data.json')
    parser.add_argument('--metrics_csv', default='output/evaluation_intent_model_experiment_level.csv', help='Path to metrics CSV for latency vs tool-F1 plot')
    parser.add_argument('--output_dir', default='output', help='Directory to save outputs')
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    # Load data
    data = load_json_data(args.data_file)
    if data is None:
        logger.error("No data loaded. Exiting.")
        return

    # Usage data
    full_summary, aggregated_summary = extract_usage_data(data)
    full_summary = sort_dataframe(full_summary, ['intent_cat', 'model_cat', 'method_cat', 'agent', 'type'])
    full_summary.to_csv(output_dir / 'usage_data.csv', index=False)
    logger.info("Saved usage_data.csv")
    
    aggregated_summary = sort_dataframe(aggregated_summary, ['intent_cat', 'model_cat', 'method_cat'])
    aggregated_summary.to_csv(output_dir / 'aggregated_usage_data.csv', index=False)
    logger.info("Saved aggregated_usage_data.csv")

    # Latency vs tool-F1 plot
    # create_latency_plot(args.metrics_csv, str(output_dir / 'latency_vs_toolf1.png'))

if __name__ == "__main__":
    main() 
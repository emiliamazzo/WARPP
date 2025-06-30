import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
import argparse


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

JSONType = Union[Dict[str, Any], List[Any]]


def load_json(path: Path) -> Optional[JSONType]:
    try:
        with path.open('r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        logging.warning(f"Failed to load JSON {path}: {e}")
        return None


def load_jsonl(path: Path) -> Optional[List[Dict[str, Any]]]:
    try:
        with path.open('r', encoding='utf-8') as f:
            return [json.loads(line) for line in f if line.strip()]
    except (json.JSONDecodeError, FileNotFoundError) as e:
        logging.warning(f"Failed to load JSONL {path}: {e}")
        return None


def read_text(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding='utf-8').strip()
    except FileNotFoundError:
        return None
    except Exception as e:
        logging.warning(f"Failed to read text {path}: {e}")
        return None


class EvaluationDataCollector:
    def __init__(self,
                base_output_dir: Union[str, Path] = "output",
                models: Optional[List[str]] = None,
                methods: Optional[List[str]] = None,
                intents: Optional[List[str]] = None):
        # auto-detect if we're running from evaluation directory
        current_dir = Path.cwd()
        base_path = Path(base_output_dir)
        
        # if we're in the evaluation directory, check for the correct output directory
        if current_dir.name == "evaluation":
            # first check if there's an output directory in the parent that has the expected structure
            parent_output = current_dir.parent / base_output_dir
            if parent_output.exists() and (parent_output / "dynamic_results").exists():
                base_output_dir = parent_output
                logging.info(f"Detected running from evaluation directory, using {parent_output}")
            elif base_path.exists() and (base_path / "dynamic_results").exists():
                # use the local output directory if it has the right structure
                logging.info(f"Using local output directory with correct structure: {base_path}")
            else:
                logging.warning(f"Output directory not found with expected structure at {base_path} or {parent_output}")
        
        self.base = Path(base_output_dir)
        self.models = models or ["gpt", "llama", "sonnet"]
        self.methods = methods or ["react", "no_parallel", "parallel"]  
        self.intents = intents or [
            "update_address", "withdraw_retirement_funds",
            "book_flight", "cancel_flight",
            "process_payment",
        ]
        self.special_methods = {"parallel", "no_parallel"}
        
        # map intents to their domains and positions within domains
        self.intent_to_domain = {
            "update_address": ("banking", 0),
            "withdraw_retirement_funds": ("banking", 1), 
            "process_payment": ("hospital", 0), 
            "book_flight": ("flights", 0),
            "cancel_flight": ("flights", 1),
        }

    def _resolve_method_dir(self, method: str) -> str:
        return f"{method}_Basic" if method in self.special_methods else method

    def _resolve_method_dir_for_category(self, method: str, category: str) -> str:
        """Resolve method directory name based on category."""
        if category in ['trajectory', 'usage', 'trimmed_routines']:
            if method == "react":
                return "react"
            elif method in self.special_methods:
                return f"{method}_Basic"
            else:
                return method
        else:
            return f"{method}_Basic" if method in self.special_methods else method

    def _extract_intent_data(self, domain_data: JSONType, intent_position: int) -> List[Dict[str, Any]]:
        """Extract the 50 records for a specific intent from domain data."""
        if not isinstance(domain_data, list):
            return []
        start_idx = intent_position * 50
        end_idx = start_idx + 50
        return domain_data[start_idx:end_idx] if domain_data else []

    def _paths_for(self, category: str, model: str, method: str, intent: str) -> Path:
        if category == 'customer':
            # map method names for dynamic_results
            dynamic_method = method
            parts = ["dynamic_results", model, dynamic_method, 'Basic'] if dynamic_method in {"parallel", "no_parallel"} else ["dynamic_results", model, dynamic_method]
            
            # get domain for intent
            if intent in self.intent_to_domain:
                domain, _ = self.intent_to_domain[intent]
                filename = f"{domain}_final.json"
            else:
                filename = f"{intent}_final.json"
            
            return self.base.joinpath(*parts, filename)

        if category == 'ground_truth':
            # map method names for gt directory  
            gt_method = method
            base = self.base / 'ground_truth_trajectory' / model / gt_method / intent
            return base / 'package.json'

        # for other categories (trajectory, usage, trimmed_routines)
        method_dir = self._resolve_method_dir_for_category(method, category)
        return self.base / category / model / method_dir / intent

    def collect(self, specific: bool = False) -> List[Dict[str, Any]]:
        configs = [
            (m, meth, i)
            for m in self.models
            for meth in self.methods
            for i in self.intents
        ]
        results = []
        logging.info(f"Collecting {len(configs)} experiments from {self.base}")

        for model, method, intent in configs:
            data = {'model': model, 'method': method, 'intent': intent, 'found': {}, 'missing': {}}

            # customer data 
            cust_path = self._paths_for('customer', model, method, intent)
            domain_data = load_json(cust_path)
            
            if domain_data and intent in self.intent_to_domain:
                domain, intent_position = self.intent_to_domain[intent]
                data['customer_data'] = self._extract_intent_data(domain_data, intent_position)
                data['found']['customer_data'] = str(cust_path)
            else:
                data['customer_data'] = domain_data  # Fallback for unknown intents
                (data['found'] if domain_data else data['missing'])['customer_data'] = str(cust_path)

            # ground truth
            gt_path = self._paths_for('ground_truth', model, method, intent)
            data['ground_truth'] = load_json(gt_path)
            (data['found'] if data['ground_truth'] else data['missing'])['ground_truth'] = str(gt_path)

            # folder-based categories
            categories_to_check = ['trajectory', 'usage']
            # only check trimmed_routines for parallel
            if method == 'parallel':
                categories_to_check.append('trimmed_routines')
            
            for category in categories_to_check:
                path = self._paths_for(category, model, method, intent)
                if not path.exists():
                    data['missing'][category] = str(path)
                    continue
                collected = []
                for file in path.iterdir():
                    if file.suffix == '.json':
                        collected.append({'file': file.name, 'data': load_json(file)})
                    elif file.suffix == '.jsonl':
                        collected.append({'file': file.name, 'data': load_jsonl(file)})
                data[f'{category}_data'] = collected
                data['found'][category] = str(path)

            results.append(data)
        return results

    def summary(self, all_data: List[Dict[str, Any]]) -> None:
        total = len(all_data)
        parallel_total = sum(1 for exp in all_data if exp['method'] == 'parallel')
        
        counts = {k: {'found': 0, 'missing': 0} for k in ['customer_data', 'ground_truth', 'trajectory', 'usage', 'trimmed_routines']}
        
        for exp in all_data:
            for cat in ['customer_data', 'ground_truth', 'trajectory', 'usage']:
                if cat in exp['found']:
                    counts[cat]['found'] += 1
                else:
                    counts[cat]['missing'] += 1
            
            # trimmed_routines only for parallel method
            if exp['method'] == 'parallel':
                if 'trimmed_routines' in exp['found']:
                    counts['trimmed_routines']['found'] += 1
                else:
                    counts['trimmed_routines']['missing'] += 1

        logging.info(f"Summary of {total} experiments:")
        for cat, stats in counts.items():
            if cat == 'trimmed_routines':
                # trimmed_routines only for parallel experiments
                pct = stats['found'] / parallel_total * 100 if parallel_total > 0 else 0
                logging.info(f"{cat}: found {stats['found']} ({pct:.1f}%), missing {stats['missing']} (out of {parallel_total} parallel experiments)")
            else:
                pct = stats['found'] / total * 100
                logging.info(f"{cat}: found {stats['found']} ({pct:.1f}%), missing {stats['missing']}")

    def save(self, data: List[Dict[str, Any]], output_file: Union[str, Path] = 'evaluation_data.json') -> None:
        eval_dir = Path(__file__).parent  # get dir where this script is located (evaluation/)
        output_path = eval_dir / output_file
        
        payload = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'base': str(self.base),
                'count': len(data)
            },
            'data': data
        }
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2)
        logging.info(f"Data saved to {output_path}")


def main():

    parser = argparse.ArgumentParser("Collect experiment evaluation data")
    parser.add_argument('--base', default='output')

    #saving and no saving flags; saving is default
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--save', dest='save', action='store_true', help='Save the output (default)')
    group.add_argument('--no-save', dest='save', action='store_false', help='Do not save the output')
    parser.set_defaults(save=True)

    args = parser.parse_args()

    collector = EvaluationDataCollector(args.base)
    data = collector.collect()
    collector.summary(data)
    if args.save:
        collector.save(data)

if __name__ == '__main__':
    main()
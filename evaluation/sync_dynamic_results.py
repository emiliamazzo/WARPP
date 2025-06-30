import json
import re
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Set, Any, Callable
from dataclasses import dataclass
from enum import Enum


class Domain(Enum):
    """Supported evaluation domains."""
    BANKING = "banking"
    FLIGHTS = "flights"
    HOSPITAL = "hospital"


@dataclass
class DomainConfig:
    """Configuration for each evaluation domain."""
    name: str
    intents: List[str]
    folder_name: str
    output_name: str


@dataclass
class FileInfo:
    """Information about a workflow or output file."""
    intent: str
    file_path: Path
    domain: Optional[str] = None


class DynamicResultsSynchronizer:
    """Synchronizes dynamic results across domains for evaluation reproducibility."""
    
    # domain configurations
    DOMAINS = {
        Domain.BANKING: DomainConfig("banking", ["update_address", "withdraw_retirement_funds"], "SimpleBanking", "Banking"),
        Domain.FLIGHTS: DomainConfig("flights", ["book_flight", "cancel_flight"], "IntermediateFlights", "Flights"),
        Domain.HOSPITAL: DomainConfig("hospital", ["process_payment"], "ComplexHospital", "Hospital")
    }
    
    # special case values for deterministic behavior
    SPECIAL_VALUES = {
        ("cancel_flight", "check_cancellation_blockers", "status"): "eligible",
        ("cancel_flight", "calculate_cancellation_fee", "cancellation_fee"): -1,
        ("process_payment", "calculate_patient_responsibility", "patient_responsibility"): -1,
        ("process_payment", "run_fraud_check", "flagged"): False,
        ("process_payment", "initiate_3ds_auth", "3ds_success_status"): True,
        ("process_payment", "initiate_ach_transaction", "ach_success_status"): "initiated",
    }
    
    RECORDS_PER_INTENT = 50
    
    def __init__(self, test_data_path: str = 'test_data', output_path: str = 'output'):
        """Initialize synchronizer with data paths."""
        current_file_dir = Path(__file__).parent.resolve()  
        base_dir = current_file_dir.parent

        self.test_data_path = base_dir / test_data_path
        self.dynamic_results_path = base_dir / output_path / 'dynamic_results'
        self.trajectory_path = base_dir / output_path / 'trajectory'
    
    
    @staticmethod
    def _safe_load_json(file_path: Path, context: str = "") -> Optional[Dict]:
        """Safely load JSON file with error handling."""
        try:
            with open(file_path) as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {context}{file_path}: {e}")
            return None
    
    @staticmethod
    def _safe_write_json(file_path: Path, data: Any, context: str = "") -> bool:
        """Safely write JSON file with error handling."""
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"    Created: {file_path}")
            return True
        except Exception as e:
            print(f"Error writing {context}{file_path}: {e}")
            return False

    @staticmethod
    def _clean_intent_name(file_path: Path, suffixes_to_remove: Optional[List[str]] = None) -> str:
        """Clean intent name by removing common suffixes."""
        name = file_path.stem
        if suffixes_to_remove:
            for suffix in suffixes_to_remove:
                name = name.replace(suffix, '')
        return name
    
    def _extract_dynamic_fields_recursive(self, value: Any, fields: Set[Tuple[str, Optional[str]]]) -> None:
        """Recursively extract dynamic_results patterns from any value."""
        if isinstance(value, str):
            matches = re.findall(r"dynamic_results\['([^']+)'\](?:\['([^']+)'\])?", value)
            fields.update((match[0], match[1] or None) for match in matches)
        elif isinstance(value, dict):
            for v in value.values():
                self._extract_dynamic_fields_recursive(v, fields)
        elif isinstance(value, list):
            for item in value:
                self._extract_dynamic_fields_recursive(item, fields)
    
    def extract_dynamic_fields(self, workflow_data: Dict[str, Any]) -> Set[Tuple[str, Optional[str]]]:
        """Extract all dynamic_results field references from workflow data."""
        fields = set()
        self._extract_dynamic_fields_recursive(workflow_data, fields)
        return fields
    
    def _generate_type_specific_value(self, expected_value: Any, operator: str) -> Any:
        """Generate value based on type and operator."""
        if isinstance(expected_value, bool):
            return random.choice([True, False])
        elif isinstance(expected_value, int):
            if operator in [">", ">="]:
                return expected_value + random.randint(1, 100)
            else:
                return max(0, expected_value - random.randint(0, 100))
        elif isinstance(expected_value, float):
            if operator in [">", ">="]:
                return expected_value + random.uniform(0.1, 100.0)
            else:
                return max(0.0, expected_value - random.uniform(0.0, 100.0))
        elif isinstance(expected_value, str):
            return expected_value if operator == "==" else f"random_{random.randint(1000, 9999)}"
        elif expected_value is None:
            return random.choice([None, "some_value", random.randint(1, 100)])
        else:
            return expected_value
    
    def generate_value(self, operator: str, expected_value: Any, 
                      tool_name: Optional[str] = None, subfield: Optional[str] = None,
                      intent: Optional[str] = None) -> Any:
        """Generate random value based on operator and expected value."""
        # Check for special case values first
        if intent and tool_name and subfield:
            special_key = (intent, tool_name, subfield)
            if special_key in self.SPECIAL_VALUES:
                return self.SPECIAL_VALUES[special_key]
        
        return self._generate_type_specific_value(expected_value, operator)
    
    def _find_matching_condition(self, conditionals: List[Dict], pattern: str) -> Tuple[str, Any]:
        """Find matching condition in workflow conditionals."""
        for conditional in conditionals:
            for condition in conditional.get('if', []):
                candidates = [condition] if 'field' in condition else condition.get('all_of') or condition.get('any_of') or []
                for item in candidates:
                    if re.match(pattern, item.get('field', '')):
                        return item.get('operator', '=='), item.get('value')
        return '==', True
    
    def get_expected_value_from_conditionals(self, conditionals: List[Dict], 
                                           tool_name: str, subfield: Optional[str]) -> Tuple[str, Any]:
        """Extract expected value and operator from workflow conditionals."""
        pattern = f"dynamic_results\\['{tool_name}'\\]"
        if subfield:
            pattern += f"\\['{subfield}'\\]"
        
        return self._find_matching_condition(conditionals, pattern)
    
    def find_workflow_files(self) -> List[FileInfo]:
        """Find all workflow files in test data."""
        files = []
        
        # look for pattern: test_data/DomainName/intent_name/full_workflow.json
        if not self.test_data_path.exists():
            return files
            
        for domain_dir in self.test_data_path.iterdir():
            if not domain_dir.is_dir() or domain_dir.name.startswith('_'):
                continue
                
            for intent_dir in domain_dir.iterdir():
                if not intent_dir.is_dir():
                    continue
                    
                workflow_file = intent_dir / 'full_workflow.json'
                if workflow_file.exists():
                    files.append(FileInfo(
                        intent=intent_dir.name,
                        file_path=workflow_file,
                        domain=domain_dir.name
                    ))
        
        return files
    
    def _process_model_directory(self, model_dir: Path, file_suffixes: List[str]) -> Dict[str, List[FileInfo]]:
        """Process a single model directory to find method files."""
        methods = {}
        
        for method_dir in model_dir.iterdir():
            if not method_dir.is_dir():
                continue
            
            method_name, files_dir = self._determine_method_structure(method_dir)
            if not files_dir:
                continue
            
            methods[method_name] = []
            
            for file in files_dir.iterdir():
                if file.is_file() and file.suffix in file_suffixes:
                    intent_name = self._clean_intent_name(file, ['_utterance', '_trajectory', '_final'])
                    methods[method_name].append(FileInfo(intent_name, file))
        
        return methods
    
    def _determine_method_structure(self, method_dir: Path) -> Tuple[str, Optional[Path]]:
        """Determine method name and files directory based on structure."""
        method_name = method_dir.name
        
        if method_name in ['parallel', 'no_parallel']:
            basic_dir = method_dir / 'Basic'
            if basic_dir.exists():
                return f"{method_name}/Basic", basic_dir
            else:
                return method_name, None
        else:
            return method_name, method_dir
    
    def find_output_files(self, base_path: Path, file_suffixes: List[str]) -> Dict[str, Dict[str, List[FileInfo]]]:
        """Find output files organized by model and method."""
        result = {}
        
        for model_dir in base_path.iterdir():
            if model_dir.is_dir():
                result[model_dir.name] = self._process_model_directory(model_dir, file_suffixes)
        
        return result
    
    def _update_tool_result(self, tool_result: Dict, tool: str, subfield: Optional[str], 
                          conditionals: List[Dict], intent: str) -> bool:
        """Update a single tool result with missing fields."""
        changed = False
        target_key = subfield or 'value'
        
        # check if the required field exists
        if target_key in tool_result:
            # field exists: only add tool_called if it doesn't already exist
            if 'tool_called' not in tool_result:
                tool_result['tool_called'] = True
                changed = True
            # if tool_called already exists, don't change it!
        else:
            # field doesn't exist: generate dummy data and mark as tool_called: false
            operator, value = self.get_expected_value_from_conditionals(conditionals, tool, subfield)
            tool_result[target_key] = self.generate_value(operator, value, tool, subfield, intent)
            tool_result['tool_called'] = False
            changed = True
        
        return changed
    
    def _create_new_tool_result(self, tool: str, subfield: Optional[str], 
                              conditionals: List[Dict], intent: str) -> Dict:
        """Create a new tool result with appropriate structure."""
        operator, value = self.get_expected_value_from_conditionals(conditionals, tool, subfield)
        random_val = self.generate_value(operator, value, tool, subfield, intent)
        
        return {
            (subfield or 'value'): random_val,
            'tool_called': False
        }
    
    def process_intent_data(self, data: List[Dict], workflow_data: Dict, intent: str) -> bool:
        """Process dynamic results for a specific intent."""
        fields = self.extract_dynamic_fields(workflow_data)
        if not fields:
            return False
        
        changed = False
        conditionals = workflow_data.get('conditionals', [])
        
        for entry in data:
            entry.setdefault('dynamic_results', {})
            
            for tool, subfield in fields:
                tool_result = entry['dynamic_results'].get(tool)
                
                # existing tool results (preserve real values)
                if tool_result is not None:
                    # if already a dict with the expected structure, just add tool_called if missing
                    if isinstance(tool_result, dict):
                        if 'tool_called' not in tool_result:
                            tool_result['tool_called'] = True
                            changed = True
                    else:
                        # real value (like a number or string): keep it
                        target_key = subfield or 'value'
                        real_value = tool_result
                        entry['dynamic_results'][tool] = {
                            target_key: real_value,
                            'tool_called': True
                        }
                        changed = True
                        continue
                else:
                    # tool result is missing: create dummy data
                    entry['dynamic_results'][tool] = self._create_new_tool_result(
                        tool, subfield, conditionals, intent
                    )
                    changed = True
                    continue
        
        return changed
    
    def write_output_files(self, file_path: Path, data: List[Dict], domain: str) -> None:
        """Write final output file."""
        final_path = file_path.with_name(f'{domain}_final.json')
        self._safe_write_json(final_path, data)

    def _load_domain_workflows(self, config: DomainConfig, workflows: Dict[str, Dict]) -> Dict[str, Dict]:
        """Load workflow data for a domain's intents."""
        intent_workflows = {}
        
        for intent in config.intents:
            workflow_key = f"{config.folder_name}/{intent}"
            if workflow_key in workflows:
                workflow_data = self._safe_load_json(
                    workflows[workflow_key]['workflow_path'], 
                    f"workflow for {intent}: "
                )
                if workflow_data:
                    intent_workflows[intent] = workflow_data
                    print(f"Loaded workflow for {intent}")
        
        return intent_workflows
    
    def _process_domain_data(self, domain_data: List[Dict], config: DomainConfig, 
                           intent_workflows: Dict[str, Dict]) -> Tuple[List[Dict], bool]:
        """Process domain data split by intents."""
        processed_data = []
        overall_changed = False
        
        for i, intent in enumerate(config.intents):
            start_idx = i * self.RECORDS_PER_INTENT
            end_idx = start_idx + self.RECORDS_PER_INTENT
            intent_data = domain_data[start_idx:end_idx]
            
            print(f"    {intent}: records {start_idx}-{end_idx-1} ({len(intent_data)} records)")
            
            if intent in intent_workflows:
                changed = self.process_intent_data(intent_data, intent_workflows[intent], intent)
                if changed:
                    overall_changed = True
                    print(f"      Modified records for {intent}")
            else:
                print(f"    Skipping {intent} - no workflow found")
            
            processed_data.extend(intent_data)
        
        return processed_data, overall_changed
    
    def process_domain(self, domain: Domain, workflows: Dict[str, Dict], output_files: Dict) -> Dict[str, List[str]]:
        """Process a single domain's data."""
        config = self.DOMAINS[domain]
        missing_files = {}
        
        print(f"\n{'='*50}")
        print(f"Processing domain: {config.name}")
        print(f"Intents: {config.intents}")
        print(f"{'='*50}")
        
        intent_workflows = self._load_domain_workflows(config, workflows)
        
        # each model/method combination
        for model, methods in output_files.items():
            for method, files in methods.items():
                domain_file = next((f for f in files if f.intent == config.name), None)
                if not domain_file:
                    missing_files.setdefault(f"{model}/{method}", []).append(config.name)
                    continue
                
                domain_data = self._safe_load_json(domain_file.file_path, f"{model}/{method}: ")
                if not domain_data:
                    continue
                
                print(f"\n  Processing {model}/{method} - {len(domain_data)} records")
                
                processed_data, overall_changed = self._process_domain_data(
                    domain_data, config, intent_workflows
                )
                
                self.write_output_files(domain_file.file_path, processed_data, config.name)
                if not overall_changed:
                    print("    No changes made, but final file generated")
        
        return missing_files
    
    def _organize_workflows(self, workflow_files: List[FileInfo]) -> Dict[str, Dict]:
        """Organize workflow files by domain/intent for easy lookup."""
        workflows = {}
        for wf in workflow_files:
            key = f"{wf.domain}/{wf.intent}"
            workflows[key] = {'workflow_path': wf.file_path}
        return workflows
    
    def _print_missing_summary(self, all_missing: Dict[str, List[str]]) -> None:
        """Print summary of missing domain files."""
        print(f"\n{'='*40}\nSUMMARY OF MISSING DOMAINS\n{'='*40}")
        if all_missing:
            for key, missing_domains in all_missing.items():
                print(f"\n{key}:")
                for domain in missing_domains:
                    print(f"  - {domain}")
        else:
            print("No missing domains found!")
    
    def run(self) -> None:
        """Execute the complete synchronization process."""
        print("Starting dynamic results synchronization...")
        
        # Find all files
        workflow_files = self.find_workflow_files()
        output_files = self.find_output_files(self.dynamic_results_path, ['.json'])
        
        print(f"Found {len(workflow_files)} workflow files")
        
        # Organize workflows and process each domain
        workflows = self._organize_workflows(workflow_files)
        all_missing = {}
        
        for domain in Domain:
            missing = self.process_domain(domain, workflows, output_files)
            all_missing.update(missing)
        
        self._print_missing_summary(all_missing)


def main():
    """Main entry point for the synchronization process."""
    synchronizer = DynamicResultsSynchronizer()
    synchronizer.run()


if __name__ == "__main__":
    main()
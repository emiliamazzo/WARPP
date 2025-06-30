import os
import json
import re
import numpy as np
from pathlib import Path
from collections import defaultdict
from statistics import mean, stdev
from typing import Any, Dict, Optional

def _compute_stats(scores: list[float]) -> dict[str, Any]:
    """Helper to compute statistics safely."""
    if not scores:
        return {}
    count = len(scores)
    avg = mean(scores)
    std_dev = stdev(scores) if count > 1 else 0.0
    return {
        'average_score': avg,
        'count': count,
        'std_dev': std_dev,
        'min_score': min(scores),
        'max_score': max(scores),
    }

def calculate_scores_by_model_and_domain(base_output_folder: str = "../output/judge_trimmed_routine") -> Optional[Dict[str, Any]]:
    """
    Calculates average scores grouped by model and domain from JSON files.

    Args:
        base_output_folder (str): Base folder with structure model/domain/*.json.

    Returns:
        dict or None: Average scores by model, domain, model-domain, and overall stats.
    """
    # Data structures for different score types
    relevance_scores_by_model = defaultdict(list)
    relevance_scores_by_domain = defaultdict(list)
    relevance_scores_by_model_domain = defaultdict(list)
    
    completeness_scores_by_model = defaultdict(list)
    completeness_scores_by_domain = defaultdict(list)
    completeness_scores_by_model_domain = defaultdict(list)

    # Track skipped files for debugging
    skipped_files = {
        'wrong_path_structure': [],
        'missing_scores': [],
        'invalid_score_values': [],
        'json_errors': [],
        'other_errors': []
    }
    
    processed_files_count = 0
    found_files_by_model_domain = defaultdict(list)

    base_path = Path(base_output_folder)
    if not base_path.exists():
        print(f"Output folder {base_output_folder} does not exist.")
        return None

    print(f"🔍 Scanning files in: {base_output_folder}")
    all_json_files = list(base_path.rglob("*.json"))
    print(f"📊 Total JSON files found: {len(all_json_files)}")

    for json_file in all_json_files:
        try:
            # Expected path structure: base/model/domain/file.json
            parts = json_file.parts
            # Find relative parts after base path
            rel_parts = json_file.relative_to(base_path).parts
            if len(rel_parts) < 3:
                # Skip files not under model/domain/
                skipped_files['wrong_path_structure'].append(str(json_file))
                continue

            model_name, domain_name = rel_parts[0], rel_parts[1]
            file_name = rel_parts[2]
            
            # Track found files by model-domain
            found_files_by_model_domain[f"{model_name}_{domain_name}"].append(file_name)

            with open(json_file, encoding='utf-8') as f:
                data = json.load(f)
            
            # Check for new format (relevance_score and completeness_score)
            relevance_score_val = data.get('relevance_score')
            completeness_score_val = data.get('completeness_score')
            
            # Fallback: try to parse from explanation field if scores are missing
            if (relevance_score_val is None or completeness_score_val is None) and 'explanation' in data:
                try:
                    # Try to parse JSON from explanation field
                    explanation_str = data['explanation']
                    # Clean up common JSON issues
                    explanation_str = explanation_str.replace('\n', '').strip()
                    # Remove trailing commas before } or ]
                    explanation_str = re.sub(r',(\s*[}\]])', r'\1', explanation_str)
                    # Fix missing colons (like "completeness_score" "4")
                    explanation_str = re.sub(r'"\s+"', '": "', explanation_str)
                    # Fix escaped backslashes that shouldn't be escaped
                    explanation_str = explanation_str.replace('\\_', '_')
                    # Replace smart quotes with regular quotes
                    explanation_str = explanation_str.replace('"', '"').replace('"', '"').replace(''', "'").replace(''', "'")
                    # Escape unescaped quotes inside string values (but not the JSON structure quotes)
                    # This is a more complex fix - let's try a simpler approach first
                    
                    explanation_data = json.loads(explanation_str)
                    if relevance_score_val is None:
                        relevance_score_val = explanation_data.get('relevance_score')
                    if completeness_score_val is None:
                        completeness_score_val = explanation_data.get('completeness_score')
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    # If still failing, try a more aggressive approach: extract scores with regex
                    try:
                        explanation_str = data['explanation']
                        relevance_match = re.search(r'"relevance_score":\s*"([^"]*)"', explanation_str)
                        completeness_match = re.search(r'"completeness_score":\s*"([^"]*)"', explanation_str)
                        
                        if relevance_score_val is None and relevance_match:
                            relevance_score_val = relevance_match.group(1)
                        if completeness_score_val is None and completeness_match:
                            completeness_score_val = completeness_match.group(1)
                    except (AttributeError, IndexError):
                        pass  # All fallbacks failed
            
            if relevance_score_val is None or completeness_score_val is None:
                skipped_files['missing_scores'].append(str(json_file))
                continue
                
            try:
                relevance_score = float(relevance_score_val)
                completeness_score = float(completeness_score_val)
                
                relevance_scores_by_model[model_name].append(relevance_score)
                relevance_scores_by_domain[domain_name].append(relevance_score)
                relevance_scores_by_model_domain[f"{model_name}_{domain_name}"].append(relevance_score)
                
                completeness_scores_by_model[model_name].append(completeness_score)
                completeness_scores_by_domain[domain_name].append(completeness_score)
                completeness_scores_by_model_domain[f"{model_name}_{domain_name}"].append(completeness_score)
                
                processed_files_count += 1
                
            except ValueError:
                skipped_files['invalid_score_values'].append(str(json_file))
                continue

        except json.JSONDecodeError as e:
            skipped_files['json_errors'].append(f"{json_file}: {e}")
            continue
        except (ValueError, FileNotFoundError, TypeError) as e:
            skipped_files['other_errors'].append(f"{json_file}: {e}")
            continue

    # Print detailed skipped files report
    print(f"\n📈 PROCESSING SUMMARY:")
    print(f"   Successfully processed: {processed_files_count} files")
    print(f"   Total skipped: {len(all_json_files) - processed_files_count} files")
    
    # Analyze missing files by comparing expected vs actual counts
    print(f"\n🔍 MISSING FILES ANALYSIS:")
    expected_models = ['gpt', 'llama', 'sonnet']
    expected_domains = ['ComplexHospital', 'IntermediateFlights', 'SimpleBanking']
    
    missing_files_found = False
    for model in expected_models:
        for domain in expected_domains:
            key = f"{model}_{domain}"
            found_count = len(found_files_by_model_domain[key])
            
            # Determine expected count based on domain
            if domain == 'ComplexHospital':
                expected_count = 50  # Assuming 50 files per model for this domain
            elif domain == 'IntermediateFlights':
                expected_count = 100  # Based on the 300 total we saw
            elif domain == 'SimpleBanking':
                expected_count = 100  # Based on the ~299 total we saw
            
            if found_count < expected_count:
                missing_files_found = True
                print(f"   ❌ {model.upper()} × {domain}: Found {found_count}, Expected {expected_count} (Missing {expected_count - found_count})")
                
                # Try to identify specific missing files by comparing with other models
                if domain in ['SimpleBanking', 'IntermediateFlights']:  # Domains with multiple models
                    # Get file lists for all models in this domain
                    model_files = {}
                    for check_model in expected_models:
                        check_key = f"{check_model}_{domain}"
                        model_files[check_model] = set(found_files_by_model_domain[check_key])
                    
                    # Find files that exist in other models but not in the current model
                    current_files = model_files[model]
                    for compare_model in expected_models:
                        if compare_model != model:
                            compare_files = model_files[compare_model]
                            missing_in_current = compare_files - current_files
                            if missing_in_current:
                                print(f"      🔍 Files in {compare_model.upper()} but missing in {model.upper()}: {sorted(missing_in_current)}")
                
                # Show sample of found files
                found_files = set(found_files_by_model_domain[key])
                print(f"      📁 Sample found files: {sorted(found_files)[:5]}..." if len(found_files) > 5 else f"      📁 Found files: {sorted(found_files)}")
                
            elif found_count > expected_count:
                print(f"   ⚠️  {model.upper()} × {domain}: Found {found_count}, Expected {expected_count} (Extra {found_count - expected_count})")
            else:
                print(f"   ✅ {model.upper()} × {domain}: Found {found_count}, Expected {expected_count} (Perfect!)")
    
    if not missing_files_found:
        print("   ✅ No missing files detected based on expected counts!")
    
    if any(skipped_files.values()):
        print(f"\n⚠️  SKIPPED FILES REPORT:")
        
        if skipped_files['wrong_path_structure']:
            print(f"\n❌ Files with wrong path structure ({len(skipped_files['wrong_path_structure'])}):")
            for file_path in skipped_files['wrong_path_structure']:
                print(f"   {file_path}")
        
        if skipped_files['missing_scores']:
            print(f"\n❌ Files missing relevance_score or completeness_score ({len(skipped_files['missing_scores'])}):")
            for file_path in skipped_files['missing_scores']:
                print(f"   {file_path}")
        
        if skipped_files['invalid_score_values']:
            print(f"\n❌ Files with invalid score values ({len(skipped_files['invalid_score_values'])}):")
            for file_path in skipped_files['invalid_score_values']:
                print(f"   {file_path}")
        
        if skipped_files['json_errors']:
            print(f"\n❌ Files with JSON parsing errors ({len(skipped_files['json_errors'])}):")
            for file_error in skipped_files['json_errors']:
                print(f"   {file_error}")
        
        if skipped_files['other_errors']:
            print(f"\n❌ Files with other errors ({len(skipped_files['other_errors'])}):")
            for file_error in skipped_files['other_errors']:
                print(f"   {file_error}")

    # Build results structure
    results = {
        'relevance_scores': {
            'by_model': {model: _compute_stats(scores) for model, scores in relevance_scores_by_model.items()},
            'by_domain': {domain: _compute_stats(scores) for domain, scores in relevance_scores_by_domain.items()},
            'by_model_domain': {md: _compute_stats(scores) for md, scores in relevance_scores_by_model_domain.items()},
        },
        'completeness_scores': {
            'by_model': {model: _compute_stats(scores) for model, scores in completeness_scores_by_model.items()},
            'by_domain': {domain: _compute_stats(scores) for domain, scores in completeness_scores_by_domain.items()},
            'by_model_domain': {md: _compute_stats(scores) for md, scores in completeness_scores_by_model_domain.items()},
        },
        'overall_stats': {},
        'skipped_files_summary': {
            'total_files_found': len(all_json_files),
            'successfully_processed': processed_files_count,
            'skipped_counts': {k: len(v) for k, v in skipped_files.items()},
            'skipped_files': skipped_files
        }
    }

    # Calculate overall statistics
    all_relevance_scores = [score for scores in relevance_scores_by_model.values() for score in scores]
    all_completeness_scores = [score for scores in completeness_scores_by_model.values() for score in scores]
    
    if all_relevance_scores:
        results['overall_stats']['relevance'] = {
            'overall_average': mean(all_relevance_scores),
            'total_files': len(all_relevance_scores),
            'overall_std_dev': stdev(all_relevance_scores) if len(all_relevance_scores) > 1 else 0.0,
            'overall_min': min(all_relevance_scores),
            'overall_max': max(all_relevance_scores),
        }
    
    if all_completeness_scores:
        results['overall_stats']['completeness'] = {
            'overall_average': mean(all_completeness_scores),
            'total_files': len(all_completeness_scores),
            'overall_std_dev': stdev(all_completeness_scores) if len(all_completeness_scores) > 1 else 0.0,
            'overall_min': min(all_completeness_scores),
            'overall_max': max(all_completeness_scores),
        }

    return results


def print_results(results: Optional[Dict[str, Any]]) -> None:
    if not results:
        print("No results to display.")
        return

    def _print_overall_stats(score_type: str, stats: dict):
        if stats:
            print(f"\n{score_type.upper()} OVERALL STATISTICS:")
            print(f"   Total Files Processed: {stats.get('total_files', 0)}")
            print(f"   Overall Average Score: {stats.get('overall_average', 0):.3f}")
            print(f"   Standard Deviation: {stats.get('overall_std_dev', 0):.3f}")
            print(f"   Score Range: {stats.get('overall_min', 0):.1f} - {stats.get('overall_max', 0):.1f}")

    def _print_group(title: str, data: dict[str, dict]):
        if not data:
            return
        print(f"\n{title}")
        print("-" * 50)
        for key, stats in sorted(data.items()):
            if stats:  # Only print if stats are not empty
                print(f"   {key.upper():<20}: {stats['average_score']:.3f} "
                      f"(σ={stats['std_dev']:.3f}, n={stats['count']})")

    # Print overall statistics for each score type
    overall_stats = results.get('overall_stats', {})
    _print_overall_stats('RELEVANCE', overall_stats.get('relevance', {}))
    _print_overall_stats('COMPLETENESS', overall_stats.get('completeness', {}))

    # Print relevance scores
    relevance_data = results.get('relevance_scores', {})
    if any(relevance_data.values()):
        print("\n" + "="*80)
        print("RELEVANCE SCORES ANALYSIS")
        print("="*80)
        _print_group("AVERAGE RELEVANCE SCORES BY MODEL:", relevance_data.get('by_model', {}))
        _print_group("AVERAGE RELEVANCE SCORES BY DOMAIN:", relevance_data.get('by_domain', {}))
        
        # Model-Domain combination with better formatting for relevance
        md_data = relevance_data.get('by_model_domain', {})
        if md_data:
            print(f"\n🔄 AVERAGE RELEVANCE SCORES BY MODEL-DOMAIN COMBINATION:")
            for md_key, stats in sorted(md_data.items()):
                if stats:  # Only print if stats are not empty
                    model, domain = md_key.split('_', 1)    
                    print(f"   {model.upper():<8} × {domain:<20}: {stats['average_score']:.3f} "
                          f"(σ={stats['std_dev']:.3f}, n={stats['count']})")

    # Print completeness scores
    completeness_data = results.get('completeness_scores', {})
    if any(completeness_data.values()):
        print("\n" + "="*80)
        print("COMPLETENESS SCORES ANALYSIS")
        print("="*80)
        _print_group("AVERAGE COMPLETENESS SCORES BY MODEL:", completeness_data.get('by_model', {}))
        _print_group("AVERAGE COMPLETENESS SCORES BY DOMAIN:", completeness_data.get('by_domain', {}))
        
        # Model-Domain combination with better formatting for completeness
        md_data = completeness_data.get('by_model_domain', {})
        if md_data:
            print(f"\n🔄 AVERAGE COMPLETENESS SCORES BY MODEL-DOMAIN COMBINATION:")
            for md_key, stats in sorted(md_data.items()):
                if stats:  # Only print if stats are not empty
                    model, domain = md_key.split('_', 1)
                    print(f"   {model.upper():<8} × {domain:<20}: {stats['average_score']:.3f} "
                          f"(σ={stats['std_dev']:.3f}, n={stats['count']})")

def save_results_to_file(results: Optional[Dict[str, Any]], output_file: str = "output/score_analysis.json") -> None:
    if not results:
        print("No results to save.")
        return

    def convert(obj):
        if isinstance(obj, (float, int, str)):
            return obj
        if isinstance(obj, dict):
            return {k: convert(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [convert(i) for i in obj]
        return str(obj)  # fallback for unknown types

    serializable = convert(results)
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(serializable, f, ensure_ascii=False, indent=4)

    print(f"\nResults saved to: {output_file}")

            
if __name__ == '__main__':
    results = calculate_scores_by_model_and_domain()
    if results:
        print_results(results)
        save_results_to_file(results)
    else:
        print("No scores found or error in processing.")

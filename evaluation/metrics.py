import json
import numpy as np
import pandas as pd
import os
import re
import ast
import sys
import difflib

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import DOMAIN_TOOLS_MAPPING, CLIENT_INFO_TOOLS_EXTRA_MAPPING
from collections import Counter

from utils import (
    normalize_string,
    parse_tool_call,
    filter_fulfillment_tools,
    get_tool_name,
    extract_user_intent,
    extract_agent_tool_sequence,
    count_turns_all,
    calculate_average_latency,
    count_errors,
    create_diff_dataframe,
)

def calculate_match_percentage(matches, total):
    """
    Compute the percentage of `matches` out of `total` and return the result
    rounded to two decimal places.

    Args:
        matches (float or int): The number of successful or matched items.
        total (float or int): The total number of items considered.

    Returns:
        float: A percentage value in [0, 100], rounded to two decimal places.
               Returns 0.0 if `total` <= 0 to avoid division-by-zero issues.
    """
    return round((matches / total) * 100, 2) if total > 0 else 0

def calculate_param_matches_any_order(tool_calls_generated, tool_calls_ground_truth):
    """
    Compute how many parameters match (and the total ground-truth parameters) 
    across two lists of tool calls, ignoring both tool-call order and reuse.

    Args:
        tool_calls_generated (list of str): The predicted tool calls.
        tool_calls_ground_truth (list of str): The reference tool calls.

    Returns:
        tuple:
          - matched_params (int): Number of parameter matches accumulated 
            across all ground-truth calls (using best local matches).
          - total_params (int): Total number of parameters in ground truth. 
            Dividing matched_params by total_params gives a match ratio.
    """
    # Create dictionaries to group tool calls by tool name
    generated_tools = {}
    ground_truth_tools = {}

    for tool in tool_calls_generated:
        tool_name, params = parse_tool_call(tool)

        if tool_name not in generated_tools:
            generated_tools[tool_name] = []
        generated_tools[tool_name].append(params)

    for tool in tool_calls_ground_truth:
        tool_name, params = parse_tool_call(tool)
        if tool_name not in ground_truth_tools:
            ground_truth_tools[tool_name] = []
        ground_truth_tools[tool_name].append(params)

    total_params = 0  # Total number of parameters in ground truth
    matched_params = 0  # Number of correctly matched parameters

    # For each tool type in ground truth
    for tool_name, ground_truth_params_list in ground_truth_tools.items():
        if tool_name in generated_tools:
            generated_params_list = generated_tools[tool_name]
            
            # For each ground truth tool call
            for gt_params in ground_truth_params_list:
                total_params += len(gt_params)  # Count all parameters in ground truth
                
                # Find best matching generated tool call for this ground truth tool call
                best_matches_for_this_call = 0
                for gen_params in generated_params_list:
                    # Count matching parameters between this ground truth and generated tool call
                    current_matches = sum(1 for param, value in gt_params.items() 
                                       if param in gen_params and gen_params[param] == value)
                    best_matches_for_this_call = max(best_matches_for_this_call, current_matches)
                
                matched_params += best_matches_for_this_call
        else:
            # If tool doesn't exist in generated, add its parameters to total but with 0 matches
            for gt_params in ground_truth_params_list:
                total_params += len(gt_params)

    return matched_params, total_params



def compute_3_tool_metrics(predicted_tools, reference_tools):
    """
    Compute precision, recall, and F1 score for tool calls, ignoring parameters
    and sequence order.

    Args:
        predicted_tools (list of str): A list of tool-call strings from the 
            predicted output.
        reference_tools (list of str): A list of tool-call strings from the 
            ground-truth reference.

    Returns:
        dict: A dictionary with three keys:
            - "precision": The multiset precision ,
            - "recall": The multiset recall,
            - "f1": The F1 score.
            All values are rounded to two decimal places.
    """

    # ignore parameters; turn each call into just "tool: X"
    pred_names = [get_tool_name(t) for t in predicted_tools]
    ref_names  = [get_tool_name(t) for t in reference_tools]

    pred_counter = Counter(pred_names)
    ref_counter  = Counter(ref_names)

    # union of all tools 
    all_keys = set(pred_counter.keys()).union(set(ref_counter.keys()))

    # True Positives: sum of overlaps; present in both predicted and reference
    TP = sum(min(pred_counter[k], ref_counter[k]) for k in all_keys)

    # False Positives: predicted tools that are not in reference
    FP = sum(
        max(pred_counter[k] - ref_counter[k], 0) 
        for k in all_keys
    )

    # False Negatives: reference tools that are not in predicted
    FN = sum(
        max(ref_counter[k] - pred_counter[k], 0)
        for k in all_keys
    )

    # Compute precision & recall
    precision = (TP / (TP + FP)) * 100 if (TP + FP) else 0.0
    recall    = (TP / (TP + FN)) * 100 if (TP + FN) else 0.0

    # F1
    f1 = 0.0
    if precision + recall > 0:
        f1 = (2 * precision * recall) / (precision + recall)

    return {'precision':round(precision, 2),
            'recall': round(recall, 2),
             'f1': round(f1, 2)
    }

def compare_trajectories(generated_list, ground_truth_list):
    """
    Compare the generated and ground-truth trajectories of agent and tool calls 
    to compute a comprehensive set of evaluation metrics.

    Args:
        generated_list (list of str): The list of actions (both agent and tool calls) 
            generated by the system.
        ground_truth_list (list of str): The reference list of actions (agent and tool calls)
            representing the ideal trajectory.

    Returns:
        dict: A dictionary containing the following keys:
            - "exact_match" (bool): True if the generated sequence exactly matches the ground truth.
            - "agent_match_percentage_any_order" (float): Percentage of ground-truth agent calls found 
              anywhere in the generated sequence.
            - "agent_match_percentage_order" (float): Percentage of ground-truth agent calls that match 
              position-by-position with the generated sequence.
            - "lcs_percentage" (float): The percentage of tool calls in the ground-truth sequence that
              are captured by the longest common subsequence (LCS) between the generated and ground-truth
              sequences.
            - "tool_precision" (float): Precision of tool calls (bag-of-tools approach).
            - "tool_recall" (float): Recall of tool calls (bag-of-tools approach).
            - "tool_f1_score" (float): F1 score for tool calls (bag-of-tools approach).
            - "fulfillment_tool_precision" (float): Precision for tool calls from fulfillment agents.
            - "fulfillment_tool_recall" (float): Recall for tool calls from fulfillment agents.
            - "fulfillment_tool_f1_score" (float): F1 score for tool calls from fulfillment agents.
            - "param_match_percentage" (float): Percentage of parameters in ground-truth tool calls that are 
              matched in the generated tool calls.
    """
    tool_calls_generated = [entry for entry in generated_list if "tool:" in entry]
    tool_calls_ground_truth = [entry for entry in ground_truth_list if "tool:" in entry]


    agents_generated = [entry for entry in generated_list if "agent:" in entry]
    agents_ground_truth = [entry for entry in ground_truth_list if "agent:" in entry]

    ### 1) Exact Match
    exact_match = (generated_list == ground_truth_list)

    ### 2) Agent matching (any order and order-based)
    ## Any order
    overlap = sum(a in agents_generated for a in agents_ground_truth)
    agent_match_percentage_any_order = round((overlap / len(agents_ground_truth)) * 100, 2)
    ## Order-based
    positions_matched = sum(1 for g, gt in zip(agents_generated, agents_ground_truth) if g == gt)
    agent_match_percentage_order = round((positions_matched / len(agents_ground_truth)) * 100, 2)

    ### 3) LCS length for all tools
    pred_names = [get_tool_name(t) for t in tool_calls_generated]
    ref_names  = [get_tool_name(t) for t in tool_calls_ground_truth]

    matcher = difflib.SequenceMatcher(None, pred_names, ref_names)
    matching_blocks = matcher.get_matching_blocks() 
    lcs_tools = sum(match.size for match in matching_blocks)
    lcs_percentage = round((lcs_tools / len(ref_names)) * 100, 2) if ref_names else 0.0

    ### 4) Precision/Recall/F1 for all tools
    all_agents_tool_metrics = compute_3_tool_metrics(tool_calls_generated, tool_calls_ground_truth)
    tool_precision = all_agents_tool_metrics["precision"]
    tool_recall = all_agents_tool_metrics["recall"]
    tool_f1_score = all_agents_tool_metrics["f1"]

    ### 5) Parameter Match for al tools (existing logic)
    param_matching_count, total_params_to_match = calculate_param_matches_any_order(
        tool_calls_generated,
        tool_calls_ground_truth
    )
    param_match_percentage = 0.0
    if total_params_to_match > 0:
        param_match_percentage = round((param_matching_count / total_params_to_match) * 100, 2)

    ### 6) Precision/Recall/F1 for Fulfillment tools
    fulfillment_metrics = compare_fulfillment_tools(generated_list, ground_truth_list)
    fulfillment_precision = fulfillment_metrics["precision"]
    fulfillment_recall = fulfillment_metrics["recall"]
    fulfillment_f1_score = fulfillment_metrics["f1"]

    return {
        "exact_match": exact_match,

        # Agents 
        "agent_match_percentage_any_order": agent_match_percentage_any_order,
        "agent_match_percentage_order": agent_match_percentage_order,

        # Tools (ALL agents)
        'lcs_tools': lcs_percentage,
        "tool_precision": tool_precision,
        "tool_recall": tool_recall,
        "tool_f1_score": tool_f1_score,

        # Tools (Fulfillment-only)
        "fulfillment_tool_precision": fulfillment_precision,
        "fulfillment_tool_recall": fulfillment_recall,
        "fulfillment_tool_f1_score": fulfillment_f1_score,

        # Parameter match (ALL agents)
        "param_match_percentage": param_match_percentage
    }

def compare_fulfillment_tools(generated_list, ground_truth_list):
    """
    Compute tool-call metrics for fulfillment agents only.

    Args:
        generated_list (list of str): A list of tool and agent call strings generated by the system.
        ground_truth_list (list of str): A list of tool and agent call strings from the reference (ground truth).

    Returns:
        dict: A dictionary containing the following keys:
            - "precision" (float): The precision of the tool calls for fulfillment agents.
            - "recall" (float): The recall of the tool calls for fulfillment agents.
            - "f1" (float): The F1 score computed from the precision and recall.
    """
    # 1) Filter out tools from Orchestrator/Authenticator
    gen_fulfillment_tools = filter_fulfillment_tools(generated_list)
    gt_fulfillment_tools  = filter_fulfillment_tools(ground_truth_list)

    # 2) Compute the 3 metrics on these filtered lists
    metrics = compute_3_tool_metrics(gen_fulfillment_tools, gt_fulfillment_tools)

    return metrics
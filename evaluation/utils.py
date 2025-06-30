import json
import numpy as np
import pandas as pd
import os
import re
import sys
import logging
from collections import Counter
from dateutil import parser
from typing import Dict, Optional, Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

try:
    from utils import DOMAIN_TOOLS_MAPPING, CLIENT_INFO_TOOLS_EXTRA_MAPPING
except ImportError:
    DOMAIN_TOOLS_MAPPING = {}
    CLIENT_INFO_TOOLS_EXTRA_MAPPING = {}

aggregation_metrics = {
            'exact_match': 'mean',
            'agent_match_%_any_order': 'mean',
            'agent_match_%_order': 'mean',
            'lcs_tools': 'mean',
            'tool_precision': 'mean',
            'tool_recall': 'mean',
            'tool_f1': 'mean',
            'fulfill_tool_precision': 'mean',
            'fulfill_tool_recall': 'mean',
            'fulfill_tool_f1': 'mean',
            'param_match_%': 'mean',
            'turns_all_agents': 'mean',
            'turns_fulfill_agents': 'mean',
            'average_latency': 'mean',
            'fulfill_agent_latency': 'mean',
            'error_count': 'mean'
        }

#################### STRING NORMALIZATION ####################
def normalize_string(input_string):
    """
    Recursively normalize an input string, list, or tuple by lowercasing,
    trimming spaces, and standardizing punctuation/parameter formatting.

    Args:
        input_string: A string to normalize (str | list | tuple | float).
    
    Returns:
        str | list: A normalized string if the input was a single value (string/tuple/float),
            or a list of normalized elements if the input was a list.    
    """
    # If list, recursion 
    if isinstance(input_string, list):
        return [normalize_string(item) for item in input_string]
    
    # If tuple, join it into a single string
    if isinstance(input_string, tuple):
        input_string = ' '.join(map(str, input_string))
    
    if isinstance(input_string, str):
        input_string = input_string.lower()
        input_string = input_string.strip()
        input_string = re.sub(' +', ' ', input_string) #extra spaces between words
        input_string = re.sub(r'\s*\.\s*', '.', input_string) #extra spaces around periods
        input_string = re.sub(r'\s*=\s*', '=', input_string) #extra spaces around =
        input_string = re.sub(r'\s*,\s*', ',', input_string) #extra spaces around commas

        # For tool calls
        if input_string.startswith('tool:'):
            # Split into tool name and parameters
            tool_parts = input_string.split('(', 1)
            if len(tool_parts) > 1:
                tool_name = tool_parts[0] 
                params = tool_parts[1].rstrip(')')  #parameters without closing parenthesis
                
                #change underscores for spaces in parameter values
                param_parts = params.split(',')
                normalized_params = []
                i = 0
                while i < len(param_parts):
                    param = param_parts[i]
                    if '=' in param:
                        key, value = param.split('=', 1)
                        key = key.strip()
                        
                        # departure_date: join all remaining parts (in case date has commas) if key is departure_date
                        if key == 'departure_date':
                            value = ','.join([value] + param_parts[i+1:]).strip()
                            i = len(param_parts)  # Skip the rest
                            
                        value = value.replace('_', ' ').strip() #underscores to spaces
                        value = re.sub(r'\s*\.\s*', '.', value) #spaces around periods

                        ###### departure_date normalization ######
                        if key == 'departure_date':
                            try:
                                # check if date is already in YYYY-MM-DD format
                                if re.match(r'^\d{4}-\d{2}-\d{2}$', value):
                                    pass
                                else:
                                    # parse any common date format, then emit YYYY-MM-DD
                                    dt = parser.parse(value)
                                    value = dt.date().isoformat()
                            except (ValueError, OverflowError):
                                print(f"couldn't parse {value}")
                                pass

                        # ######zip_code normalization######
                        if key == 'zip_code':
                            # Strip '-0000' suffix if present
                            if value.endswith('-0000'):
                                value = value[:-5]  # Remove the last 5 characters ('-0000')

                        # normalize numeric values in parameters to integers
                        if key != 'zip_code':
                            try:
                                numeric_val = float(value)
                                # round all numbers to integers to eliminate precision issues
                                value = str(int(round(numeric_val)))
                            except (ValueError, TypeError):
                                pass
                        
                        # if value.lower().startswith("dr."): #just keep dr without name 
                        #     value = "dr."
                        normalized_params.append(f"{key.strip()}={value}")
                    else:
                        normalized_params.append(param.strip())
                    i += 1
                
                # reconstruct the tool call
                input_string = f"{tool_name}({','.join(normalized_params)})"

    elif isinstance(input_string, float):
        input_string = str(int(round(input_string)))
    
    return input_string


def normalize_agent_name(agent_name_with_prefix):
    """Normalize agent names to standardized format."""
    if not isinstance(agent_name_with_prefix, str):
        return agent_name_with_prefix
    
    agent_name = agent_name_with_prefix
    
    # remove <>
    agent_name = re.sub(r'[<>]', '', agent_name)
    
    # remove "agent:" 
    if agent_name.lower().startswith("agent:"):
        agent_name = agent_name[6:].strip()
    
    # normalize 
    agent_name = agent_name.lower().strip()
    
    # Map common variations to standard names
    agent_name_mapping = {
        'basicreactagent': 'BasicReActAgent',
        'reactagent': 'ReActAgent', 
        'orchestratoragent': 'OrchestratorAgent',
        'authenticatoragent': 'AuthenticatorAgent',
        'book_flight': 'book_flight',
        'cancel_flight': 'cancel_flight', 
        'process_payment': 'process_payment',
        'update_address': 'update_address',
        'check_balance': 'check_balance',
        'transfer_funds': 'transfer_funds',
        'get_medical_history': 'get_medical_history',
        'schedule_appointment': 'schedule_appointment',
        'renew_prescription': 'renew_prescription',
    }
    
    standardized_name = agent_name_mapping.get(agent_name, agent_name)
    return f"agent: {standardized_name}"


####################TOOL PARSING####################

def parse_tool_call(tool_call):
    """
    Parses a tool call string into tool name and parameters from a string
    in the format "toolName(param1=val1, param2=val2)".

    Args:
        tool_call (str): A string representing a tool call, for example:
                         "myTool(param1=123, param2=abc)".

    Returns:
        tuple:
            A tuple of (tool_name, params_dict), where:
              - tool_name (str) is the substring before '(' (trimmed),
              - params_dict (dict) is a mapping of parameter keys to string values.
                If there are no parameters, returns an empty dict.
    """
    tool_call_split = tool_call.split('(')
    tool_name = tool_call_split[0].strip()  
    params_str = tool_call_split[1].split(')')[0] if len(tool_call_split) > 1 else ''

    # check if there are parameters to parse
    if params_str:
        params = params_str.split(',')
        params_dict = {}
        
        for param in params:
            param_parts = param.split('=')
            if len(param_parts) == 2:  # two parts (key and value)
                key, value = param_parts
                params_dict[key.strip()] = value.strip()
        return tool_name, params_dict
    else:
        return tool_name, {}


def get_tool_name(tool_call):
    """
    Extract the tool name from a tool call string, ignoring any parameters.

    Args:
        tool_call (str): A string representing a tool call, e.g. "tool: deposit(amount=100)".

    Returns:
        str: The tool name extracted from the input string, e.g. "tool: deposit".
    """
    return tool_call.split('(')[0].strip() if '(' in tool_call else tool_call


def filter_fulfillment_tools(sequence):
    """
    Filter out tool calls made by OrchestratorAgent or AuthenticatorAgent, returning only
    those calls made by fulfillment agents. For react experiments, filters out
    specific authentication related tools (non-fulfillment tools)

    Args:
        sequence (list of str): A list of entries, e.g., 
            Each "agent:" item sets the current agent; each "tool:" item is conditionally filtered.

    Returns:
        list of str: A list containing only the "tool:" calls that should be included.
    """
    excluded_agents = {"agent: orchestratoragent", "agent: authenticatoragent"}
    excluded_tools = {"send_verification_text", "code_verifier"}
    current_agent = None
    filtered_tools = []
    
    # Detect if this is react 
    agent_entries = [item for item in sequence if item.startswith("agent:")]
    is_react_agent = len(agent_entries) == 1 and "reactagent" in agent_entries[0].lower()

    for item in sequence:
        if item.startswith("agent:"):
            current_agent = normalize_agent_name(item).lower()
        elif item.startswith("tool:"):
            if is_react_agent:
                # For react experiments, filter by tool name
                tool_name = item.split('(')[0].replace('tool: ', '')
                if tool_name not in excluded_tools:
                    filtered_tools.append(item)
            else:
                # For multi-agent experiments, filter by agent
                if current_agent not in excluded_agents:
                    filtered_tools.append(item)
    
    return filtered_tools


def get_react_fulfillment_data_start_index(data):
    """
    For React agents, determine the start index in raw data for fulfillment-only analysis.
    Returns the index after the last code_verifier tool, or after the last send_verification_text
    if code_verifier doesn't exist, or 0 if neither exists.
    
    Args:
        data (list): Raw trajectory data as list of dicts.
        
    Returns:
        int: The start index for fulfillment analysis in the raw data.
    """
    agent_entries = []
    for log in data:
        if log["event_type"] == "agent_response" and "current_agent" in log.get("data", {}):
            agent_entries.append(log["data"]["current_agent"])
    
    is_react_agent = len(set(agent_entries)) == 1 and "reactagent" in agent_entries[0].lower() if agent_entries else False
    
    if not is_react_agent:
        return 0  # for non-react agents, start from beginning
    
    # find last occurrence of authentication tools
    last_code_verifier_idx = -1
    last_send_verification_idx = -1
    
    for i, log in enumerate(data):
        if log["event_type"] == "tool_called":
            tool_name = log["data"]["tool_name"]
            if tool_name == "code_verifier":
                last_code_verifier_idx = i
            elif tool_name == "send_verification_text":
                last_send_verification_idx = i
    
    # return index after the last authentication tool
    if last_code_verifier_idx >= 0:
        return last_code_verifier_idx + 1
    elif last_send_verification_idx >= 0:
        return last_send_verification_idx + 1
    else:
        return 0  # no authentication tools found, start from beginning


#################### DATA EXTRACTION ####################

def extract_user_intent(source):
    """
    Extract the user ID and high-level intent from a JSONL log file or structured data.

    Args:
        source (str or list): Path to the .jsonl file or list of dicts.

    Returns:
        tuple: (user_id, intent_from_trajectory)
    """
    if isinstance(source, str):
        with open(source, "r") as file:
            data = [json.loads(line.strip()) for line in file]
    else:
        data = source
    user_id, intent_from_trajectory = None, None
    for log in data:
        if log["event_type"] == "user_id":
            user_id = log["data"]["id"]
        elif log["event_type"] == "tool_called" and log["data"]["tool_name"] == "intent_identified":
            intent_from_trajectory = json.loads(log["data"]["arguments"]).get("intent")
            break
    return user_id, intent_from_trajectory


def extract_agent_tool_sequence(source):
    """
    Read a JSONL log file or structured data and produce a sequence of "agent: X" and "tool: Y(...)" entries.

    Args:
        source (str or list): Path to the .jsonl file or list of dicts.

    Returns:
        list of str: A chronological list of agent and tool call statements.
    """
    if isinstance(source, str):
        with open(source, "r") as file:
            data = [json.loads(line.strip()) for line in file]
    else:
        data = source
    sequence = []
    last_agent = None  # to avoid duplicates
    for log in data:
        event_type = log["event_type"]
        data_ = log["data"]
        if event_type == "error":
            continue
        if "current_agent" in data_:
            current_agent = normalize_agent_name(f"agent: {data_['current_agent']}")
            if current_agent != last_agent:
                sequence.append(current_agent)
                last_agent = current_agent
        if event_type == "tool_called":
            tool_name = data_["tool_name"]
            arguments = data_.get("arguments", "{}")
            try:
                arguments_dict = json.loads(arguments)
                formatted_args = []
                for k, v in arguments_dict.items():
                    if isinstance(v, (int, float)):
                        formatted_value = str(int(round(float(v))))
                    elif isinstance(v, (str, bool)) or v is None:
                        formatted_value = str(v)
                    else:
                        formatted_value = str(v)
                    formatted_args.append(f"{k}={formatted_value}")
                arguments_str = ", ".join(formatted_args)
            except json.JSONDecodeError:
                arguments_str = arguments
            sequence.append(f"tool: {tool_name}({arguments_str})")
    return sequence


def count_turns_all(source, fulfillment=False):
    """
    Count the number of user input turns in a trajectory log file or structured data.

    Args:
        source (str or list): Path to the trajectory log file or list of dicts.
        fulfillment (bool, optional): If True, count only turns for fulfillment agents.

    Returns:
        int: The total number of user input turns counted.
    """
    if isinstance(source, str):
        with open(source, "r") as file:
            data = [json.loads(line.strip()) for line in file]
    else:
        data = source
    
    # for fulfillment=True, we need to get the start index for react 
    if fulfillment:
        start_index = get_react_fulfillment_data_start_index(data)
        data = data[start_index:]
    
    turn_count = 0
    current_agent = None 
    for log in data:
        event_type = log["event_type"]
        data_ = log.get("data", {})
        # track current agent and switch events
        if event_type == "agent_response" and "current_agent" in data_:
            current_agent = data_["current_agent"]
            
        #count turns for all agents if fulfillemnt is False    
        if not fulfillment and event_type == "user_input":
            turn_count += 1

        # count turn for fullfilment agents only if fulfillment is true
        if fulfillment and event_type == "user_input":
            if current_agent not in ["OrchestratorAgent", "AuthenticatorAgent"]:
                turn_count += 1
            
    return turn_count


def calculate_average_latency(source, fulfillment=False):
    """
    Calculate the average perceived latency of the agents from a trajectory file or structured data.
    Args:
        source (str or list): Path to the trajectory file or list of dicts.
        fulfillment (bool): If True, calculate latency for fulfillment agents only.
    Returns:
        float: Average latency for the selected agent type.
    """
    if isinstance(source, str):
        with open(source, "r") as file:
            data = [json.loads(line.strip()) for line in file]
    else:
        data = source
    
    # for fulfillment=True, we need to get the start index for React
    if fulfillment:
        start_index = get_react_fulfillment_data_start_index(data)
        data = data[start_index:]
        
    latencies = []
    current_agent = None
    
    for log in data:
        event_type = log["event_type"]
        data_ = log.get("data", {})

        #track current agent
        if event_type == "agent_response" and "current_agent" in data_:
            current_agent = data_["current_agent"]

        if event_type == "agent_response" and "user_perceived_latency" in data_:
            #if fulfillment is false, count latencies for all agents.
            if not fulfillment:
                latencies.append(data_["user_perceived_latency"])

            #if fullfilment is true, count latencies for non orch or auth agents. 
            elif fulfillment:
                if current_agent not in ["OrchestratorAgent", "AuthenticatorAgent"]:
                    latencies.append(data_["user_perceived_latency"])
                
    return round(float(np.mean(latencies)), 2) if latencies else 0.0


def count_errors(source):
    """
    Count the number of error events in a JSONL log file or structured data.
    Args:
        source (str or list): Path to the JSONL log file or list of dicts.
    Returns:
        int: The total number of error events found in the file/data.
    """
    if isinstance(source, str):
        with open(source, "r") as file:
            data = [json.loads(line.strip()) for line in file]
    else:
        data = source
    error_count = 0
    for log in data:
        if log.get("event_type") == "error":
            error_count += 1
    return error_count


#################### DELTA AND % CHANGE CALCULATIONS ####################
def _calculate_differences_and_percentage_changes(df_merged, df_diff, col1, col2, comparison_name, base_name):
    """
    Helper function to calculate differences and percentage changes between two columns.
    Args:
        df_merged (pd.DataFrame): Merged dataframe with all experiment data
        df_diff (pd.DataFrame): Output dataframe to store results
        col1 (str): First column name (typically with suffix)
        col2 (str): Second column name (typically without suffix)
        comparison_name (str): Name for the comparison (e.g., "parallel_vs_react")
        base_name (str): The metric base name (e.g., 'accuracy')
    """
    if col2 in df_merged.columns:
        diff_col = f"delta_{base_name}_{comparison_name}"
        pct_col = f"pct_change_{base_name}_{comparison_name}"

        #delta
        df_diff[diff_col] = round(df_merged[col1] - df_merged[col2], 2)
        
        ###percentage change

        #vals of col are just 0 or 1 (former boolean)
        if df_merged[col2].dtype == int and set(df_merged[col2].unique()).issubset({0, 1}):
            df_diff[pct_col] = df_diff[diff_col] * 100
            
        else:
            df_diff[pct_col] = np.nan
            non_zero_mask = df_merged[col2] != 0 #get only rows with denominator is not 0
            df_diff.loc[non_zero_mask, pct_col] = round((
                (df_merged.loc[non_zero_mask, col1] - df_merged.loc[non_zero_mask, col2])
                / df_merged.loc[non_zero_mask, col2]
            ) * 100, 2)
    else:
        print(f"DEBUG: Missing column {col2}")


def create_diff_dataframe(client_df):
    """
    Merge metrics to compute differences and percentage changes between three experiment types:
    "react", "no_parallel", and "parallel".
    Args:
        client_df (pd.DataFrame): A DataFrame containing client-level metrics with columns including:
            - A unique identifier (e.g., 'customer_id')
            - 'experiment_type' with values "react", "no_parallel", and "parallel"
            - 'model' with values like "gpt", "llama", "sonnet"
            - Several numeric metric columns
    Returns:
        pd.DataFrame: A DataFrame that merges metrics for each client across all three experiment types, with new
        columns added for:
            - Absolute differences (prefixed with "delta_")
            - Percentage changes (prefixed with "pct_change_")
            - Comparisons: parallel-no_parallel, parallel-react, no_parallel-react
    """
    df_parallel = client_df[client_df["experiment_type"] == "parallel"].copy()
    df_no_parallel = client_df[client_df["experiment_type"] == "no_parallel"].copy()
    df_react = client_df[client_df["experiment_type"] == "react"].copy()
    
    merge_cols = ["customer_id", "domain", "intent", "model"]
    
    # merge 3 dfs
    df_merged = pd.merge(
        df_parallel, df_no_parallel, 
        on=merge_cols, 
        suffixes=("_parallel", "_no_parallel"), 
        how="inner"
    )
    df_merged = pd.merge(
        df_merged, df_react,
        on=merge_cols,
        how="inner"
    )
    # convert bool columns to int
    for col in df_merged.columns:
        if pd.api.types.is_bool_dtype(df_merged[col]):
            df_merged[col] = df_merged[col].astype(int)
            
    #  all columns detected as numeric
    all_numeric_cols = [col for col in df_merged.columns if pd.api.types.is_numeric_dtype(df_merged[col])]
    
    # get numeric columns for each experiment type using all_numeric_cols
    numeric_cols_parallel = [col for col in all_numeric_cols if col.endswith('_parallel') and not col.endswith('_no_parallel')]
    numeric_cols_no_parallel = [col for col in all_numeric_cols if col.endswith('_no_parallel')]
    numeric_cols_react = [col for col in all_numeric_cols if not col.endswith(('_parallel', '_no_parallel')) and col not in merge_cols] #react
    
    # output df 
    df_diff = df_merged[merge_cols].copy()
    
    comparisons = [
        # (col1_suffix, col2_suffix, comparison_name, col1_list)
        ('_parallel', '_no_parallel', 'parallel_vs_no_parallel', numeric_cols_parallel),
        ('_parallel', '', 'parallel_vs_react', numeric_cols_parallel),
        ('_no_parallel', '', 'no_parallel_vs_react', numeric_cols_no_parallel)
    ]
    # get diff and % changes for all comparisons
    for col1_suffix, col2_suffix, comparison_name, col1_list in comparisons:
        for col1 in col1_list:
            if col1_suffix == '_no_parallel' and col2_suffix == '':
                # for no_parallel vs react, col2 is the base name (without _no_parallel suffix)
                base_name = col1.replace('_no_parallel', '')
                col2 = base_name
            else:
                base_name = col1.replace(col1_suffix, "")
                col2 = base_name + col2_suffix if col2_suffix else base_name
            _calculate_differences_and_percentage_changes(
                df_merged, df_diff, col1, col2, comparison_name, base_name
            )
    return df_diff

def get_customer_trajectory_data(trajectory_data, customer_id):
    """
    Get trajectory data for a specific customer from a list of trajectory files.
    
    Args:
        trajectory_data (list): List of trajectory file objects, each with 'file' and 'data' keys.
        customer_id (str): The customer ID to search for.
        
    Returns:
        dict or None: The trajectory data for the customer, or None if not found.
    """
    for trajectory_file in trajectory_data:
        filename = trajectory_file.get('file', '')
        file_customer_id = filename.replace('.jsonl', '') if filename.endswith('.jsonl') else filename
        if str(file_customer_id) == str(customer_id):
            return trajectory_file
    return None


def extract_ground_truth_trajectory(ground_truth_data, customer_id):
    """
    Extract ground truth trajectory for a specific customer.
    
    Args:
        ground_truth_data (dict): Ground truth data containing customer trajectories.
        customer_id (str): The customer ID to extract trajectory for.
        
    Returns:
        list: The ground truth trajectory actions for the customer.
    """
    customer_trajectory = ground_truth_data.get(str(customer_id), {})
    traxgen_data = customer_trajectory.get('traxgen', [])
    
    if not traxgen_data:
        return []
    
    # flatten the nested list if necessary
    if isinstance(traxgen_data[0], list):
        return traxgen_data[0]
    return traxgen_data

def sort_dataframe(df, sort_columns):
    """Helper function to sort dataframe with custom ordering."""
    intent_order = ['update_address', 'withdraw_retirement_funds', 'book_flight', 'cancel_flight', 'process_payment']
    experiment_type_order = ['react', 'no_parallel', 'parallel']
    model_order = ['llama', 'gpt', 'sonnet']
    
    df_sorted = df.copy()
    
    # categorical columns for sorting
    if 'intent' in df_sorted.columns:
        df_sorted['intent_cat'] = pd.Categorical(df_sorted['intent'], categories=intent_order, ordered=True)
    if 'experiment_type' in df_sorted.columns:
        df_sorted['experiment_type_cat'] = pd.Categorical(df_sorted['experiment_type'], categories=experiment_type_order, ordered=True)
    if 'method' in df_sorted.columns:
        df_sorted['method_cat'] = pd.Categorical(df_sorted['method'], categories=experiment_type_order, ordered=True)
    if 'model' in df_sorted.columns:
        df_sorted['model_cat'] = pd.Categorical(df_sorted['model'], categories=model_order, ordered=True)
    
    df_sorted = df_sorted.sort_values(sort_columns)
    df_sorted = df_sorted.drop([col for col in ['intent_cat', 'experiment_type_cat', 'method_cat', 'model_cat'] if col in df_sorted.columns], axis=1)
    
    return df_sorted 


def load_json_data(file_path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        logger.info(f"Loaded data from {file_path}")
        return data
    except Exception as e:
        logger.error(f"Failed to load {file_path}: {e}")
        return None
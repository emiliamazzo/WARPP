import unittest
import json
import pandas as pd
import numpy as np
import tempfile
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils import (
    normalize_string,
    normalize_agent_name,
    parse_tool_call,
    get_tool_name,
    filter_fulfillment_tools,
    get_react_fulfillment_data_start_index,
    extract_user_intent,
    extract_agent_tool_sequence,
    count_turns_all,
    calculate_average_latency,
    count_errors,
    create_diff_dataframe,
    get_customer_trajectory_data,
    extract_ground_truth_trajectory
)

from metrics import (
    calculate_match_percentage,
    calculate_param_matches_any_order,
    compute_3_tool_metrics,
    compare_trajectories,
    compare_fulfillment_tools
)


class TestUtilsFunctions(unittest.TestCase):
    """Test cases for utility functions from utils.py"""

    def test_normalize_string_basic(self):
        """Test basic string normalization"""
        # Test basic string normalization
        self.assertEqual(normalize_string("  Hello World  "), "hello world")
        self.assertEqual(normalize_string("Test=Value"), "test=value")
        self.assertEqual(normalize_string("Test . Value"), "test.value")
        
        # Test list normalization
        result = normalize_string(["  Hello  ", "  World  "])
        self.assertEqual(result, ["hello", "world"])
        
        # Test tuple normalization
        result = normalize_string(("  Hello  ", "  World  "))
        self.assertEqual(result, "hello world")
        
        # Test float normalization
        self.assertEqual(normalize_string(3.7), "4")

    def test_normalize_string_tool_calls(self):
        """Test tool call string normalization"""
        # Test basic tool call
        tool_call = "tool: book_flight(departure_date=2024-01-15, destination=New_York)"
        expected = "tool: book_flight(departure_date=2024-01-15,destination=new york)"
        self.assertEqual(normalize_string(tool_call), expected)
        
        # Test tool call with numeric parameters
        tool_call = "tool: transfer_funds(amount=100.6, account=12345)"
        expected = "tool: transfer_funds(amount=101,account=12345)" 
        self.assertEqual(normalize_string(tool_call), expected)
        
        # Test tool call with zip code
        tool_call = "tool: update_address(zip_code=12345-0000, city=Boston)"
        expected = "tool: update_address(zip_code=12345,city=boston)"
        self.assertEqual(normalize_string(tool_call), expected)
        
        # Test zip code without suffix
        tool_call = "tool: update_address(zip_code=12345, city=Boston)"
        expected = "tool: update_address(zip_code=12345,city=boston)"
        self.assertEqual(normalize_string(tool_call), expected)
        
        # Test date in different format (if parser is available)
        tool_call = "tool: book_flight(departure_date=January 15, 2024, destination=NYC)"
        # The normalize_string function should try to parse this and convert to YYYY-MM-DD
        result = normalize_string(tool_call)
        self.assertIn("departure_date=", result)
        self.assertIn("destination=nyc", result)

    def test_normalize_string_edge_cases(self):
        """Test edge cases for string normalization"""
        # Test empty string
        self.assertEqual(normalize_string(""), "")
        
        # Test None
        self.assertEqual(normalize_string(None), None)
        
        # Test tool call with no parameters
        tool_call = "tool: check_balance()"
        expected = "tool: check_balance()"
        self.assertEqual(normalize_string(tool_call), expected)
        
        # Test tool call with spaces around parameters
        tool_call = "tool: book_flight( departure_date = 2024-01-15 , destination = NYC )"
        expected = "tool: book_flight(departure_date=2024-01-15,destination=nyc)"
        self.assertEqual(normalize_string(tool_call), expected)

    def test_normalize_agent_name(self):
        """Test agent name normalization"""
        # Test basic normalization
        self.assertEqual(normalize_agent_name("agent: BasicReActAgent"), "agent: BasicReActAgent")
        self.assertEqual(normalize_agent_name("<agent: ReActAgent>"), "agent: ReActAgent")
        self.assertEqual(normalize_agent_name("Agent: OrchestratorAgent"), "agent: OrchestratorAgent")
        
        # Test mapping variations
        self.assertEqual(normalize_agent_name("basicreactagent"), "agent: BasicReActAgent")
        self.assertEqual(normalize_agent_name("reactagent"), "agent: ReActAgent")
        
        # Test non-string input
        self.assertEqual(normalize_agent_name(123), 123)

    def test_parse_tool_call(self):
        """Test tool call parsing"""
        # Test tool call with parameters
        tool_call = "book_flight(departure_date=2024-01-15, destination=NYC)"
        tool_name, params = parse_tool_call(tool_call)
        self.assertEqual(tool_name, "book_flight")
        self.assertEqual(params, {"departure_date": "2024-01-15", "destination": "NYC"})
        
        # Test tool call without parameters
        tool_call = "check_balance()"
        tool_name, params = parse_tool_call(tool_call)
        self.assertEqual(tool_name, "check_balance")
        self.assertEqual(params, {})
        
        # Test tool call with spaces
        tool_call = "transfer_funds( amount = 100 , account = 12345 )"
        tool_name, params = parse_tool_call(tool_call)
        self.assertEqual(tool_name, "transfer_funds")
        self.assertEqual(params, {"amount": "100", "account": "12345"})

    def test_get_tool_name(self):
        """Test tool name extraction"""
        self.assertEqual(get_tool_name("tool: book_flight(departure_date=2024-01-15)"), "tool: book_flight")
        self.assertEqual(get_tool_name("check_balance()"), "check_balance")
        self.assertEqual(get_tool_name("transfer_funds"), "transfer_funds")

    def test_filter_fulfillment_tools_non_react(self):
        """Test fulfillment tool filtering for non-react (multi-agent) experiments"""
        # Test multi-agent sequence with OrchestratorAgent, AuthenticatorAgent, and fulfillment agent
        sequence = [
            "agent: OrchestratorAgent",
            "tool: send_verification_text(phone=1234567890)",
            "agent: AuthenticatorAgent",
            "tool: code_verifier(code=123456)",
            "agent: UpdateAddress",  # Fulfillment agent
            "tool: validate_address(zip_code=12345, city=Boston)",
            "tool: update_address(zip_code=12345, city=Boston)",
            "tool: close_case(customer_id=1234567890)"
        ]
        filtered = filter_fulfillment_tools(sequence)
        expected = ["tool: validate_address(zip_code=12345, city=Boston)",
         "tool: update_address(zip_code=12345, city=Boston)",
         "tool: close_case(customer_id=1234567890)"]
        self.assertEqual(filtered, expected)

    def test_filter_fulfillment_tools_react(self):
        """Test fulfillment tool filtering for React experiments"""
        # Test React agent sequence (single agent only)
        sequence = [
            "agent: ReActAgent",
            "tool: send_verification_text(phone=1234567890)",
            "tool: book_flight(departure_date=2024-01-15)",
            "tool: code_verifier(code=123456)",
            "tool: check_balance()"
        ]
        filtered = filter_fulfillment_tools(sequence)
        expected = ["tool: book_flight(departure_date=2024-01-15)", "tool: check_balance()"]
        self.assertEqual(filtered, expected)

    def test_get_react_fulfillment_data_start_index(self):
        """Test React fulfillment data start index calculation"""
        # Test data with authentication tools
        data = [
            {"event_type": "agent_response", "data": {"current_agent": "ReActAgent"}},
            {"event_type": "tool_called", "data": {"tool_name": "send_verification_text"}},
            {"event_type": "tool_called", "data": {"tool_name": "code_verifier"}},
            {"event_type": "tool_called", "data": {"tool_name": "book_flight"}},
        ]
        start_index = get_react_fulfillment_data_start_index(data)
        self.assertEqual(start_index, 3)  # Should start after code_verifier
        
        # Test data without authentication tools
        data = [
            {"event_type": "agent_response", "data": {"current_agent": "ReActAgent"}},
            {"event_type": "tool_called", "data": {"tool_name": "book_flight"}},
        ]
        start_index = get_react_fulfillment_data_start_index(data)
        self.assertEqual(start_index, 0)  # Should start from beginning

    def test_extract_user_intent(self):
        """Test user intent extraction"""
        data = [
            {"event_type": "user_id", "data": {"id": "customer123"}},
            {"event_type": "tool_called", "data": {"tool_name": "intent_identified", "arguments": '{"intent": "book_flight"}'}},
        ]
        user_id, intent = extract_user_intent(data)
        self.assertEqual(user_id, "customer123")
        self.assertEqual(intent, "book_flight")

    def test_extract_agent_tool_sequence(self):
        """Test agent tool sequence extraction"""
        data = [
            {"event_type": "agent_response", "data": {"current_agent": "BasicReActAgent"}},
            {"event_type": "tool_called", "data": {"tool_name": "book_flight", "arguments": '{"departure_date": "2024-01-15"}'}},
            {"event_type": "agent_response", "data": {"current_agent": "OrchestratorAgent"}},
            {"event_type": "tool_called", "data": {"tool_name": "check_balance", "arguments": "{}"}},
        ]
        sequence = extract_agent_tool_sequence(data)
        expected = [
            "agent: BasicReActAgent",
            "tool: book_flight(departure_date=2024-01-15)",
            "agent: OrchestratorAgent", 
            "tool: check_balance()"
        ]
        self.assertEqual(sequence, expected)

    def test_count_turns_all_non_react(self):
        """Test turn counting for non-react (multi-agent) experiments"""
        data = [
            {"event_type": "user_input"},
            {"event_type": "agent_response", "data": {"current_agent": "OrchestratorAgent"}},
            {"event_type": "user_input"},
            {"event_type": "agent_response", "data": {"current_agent": "UpdateAddressAgent"}},
        ]
        self.assertEqual(count_turns_all(data), 2)
        self.assertEqual(count_turns_all(data, fulfillment=True), 1)  # Only UpdateAddressAgent

    def test_count_turns_all_react(self):
        """Test turn counting for React experiments"""
        data = [
            {"event_type": "user_input"},
            {"event_type": "agent_response", "data": {"current_agent": "ReActAgent"}},
            {"event_type": "user_input"},
            {"event_type": "agent_response", "data": {"current_agent": "ReActAgent"}},
        ]
        self.assertEqual(count_turns_all(data), 2)
        self.assertEqual(count_turns_all(data, fulfillment=True), 2)  # All turns for ReActAgent

    def test_calculate_average_latency_non_react(self):
        """Test average latency calculation for non-react experiments"""
        data = [
            {"event_type": "agent_response", "data": {"current_agent": "OrchestratorAgent", "user_perceived_latency": 1.5}},
            {"event_type": "agent_response", "data": {"current_agent": "UpdateAddressAgent", "user_perceived_latency": 2.0}},
            {"event_type": "agent_response", "data": {"current_agent": "OrchestratorAgent", "user_perceived_latency": 1.0}},
        ]
        self.assertEqual(calculate_average_latency(data), 1.5)  # Average of all
        self.assertEqual(calculate_average_latency(data, fulfillment=True), 2.0)  # Average of UpdateAddressAgent only

    def test_calculate_average_latency_react(self):
        """Test average latency calculation for React experiments"""
        data = [
            {"event_type": "agent_response", "data": {"current_agent": "ReActAgent", "user_perceived_latency": 1.5}},
            {"event_type": "agent_response", "data": {"current_agent": "ReActAgent", "user_perceived_latency": 2.0}},
            {"event_type": "agent_response", "data": {"current_agent": "ReActAgent", "user_perceived_latency": 1.0}},
        ]
        self.assertEqual(calculate_average_latency(data), 1.5)  # Average of all
        self.assertEqual(calculate_average_latency(data, fulfillment=True), 1.5)  # Same average for ReActAgent

    def test_count_errors(self):
        """Test error counting"""
        data = [
            {"event_type": "user_input"},
            {"event_type": "error", "data": {"message": "Tool not found"}},
            {"event_type": "agent_response"},
            {"event_type": "error", "data": {"message": "Invalid parameter"}},
        ]
        self.assertEqual(count_errors(data), 2)

    def test_create_diff_dataframe(self):
        """Test difference dataframe creation"""
        # Create test data
        test_data = pd.DataFrame({
            'customer_id': ['1', '1', '1', '2', '2', '2'],
            'domain': ['travel', 'travel', 'travel', 'banking', 'banking', 'banking'],
            'intent': ['book_flight', 'book_flight', 'book_flight', 'check_balance', 'check_balance', 'check_balance'],
            'model': ['gpt', 'gpt', 'gpt', 'llama', 'llama', 'llama'],
            'experiment_type': ['parallel', 'no_parallel', 'react', 'parallel', 'no_parallel', 'react'],
            'accuracy': [0.9, 0.8, 0.7, 0.85, 0.75, 0.65],
            'latency': [1.5, 2.0, 1.8, 1.2, 1.8, 1.5]
        })
        
        result = create_diff_dataframe(test_data)
        
        # Check that result has the expected columns
        expected_cols = ['customer_id', 'domain', 'intent', 'model']
        for col in expected_cols:
            self.assertIn(col, result.columns)
        
        # Check that difference columns were created
        diff_cols = [col for col in result.columns if col.startswith('delta_')]
        self.assertGreater(len(diff_cols), 0)

    def test_get_customer_trajectory_data(self):
        """Test customer trajectory data retrieval"""
        trajectory_data = [
            {'file': 'customer123.jsonl', 'data': [{'event_type': 'user_input'}]},
            {'file': 'customer456.jsonl', 'data': [{'event_type': 'agent_response'}]},
        ]
        
        result = get_customer_trajectory_data(trajectory_data, 'customer123')
        self.assertEqual(result['file'], 'customer123.jsonl')
        
        result = get_customer_trajectory_data(trajectory_data, 'nonexistent')
        self.assertIsNone(result)

    def test_extract_ground_truth_trajectory(self):
        """Test ground truth trajectory extraction"""
        ground_truth_data = {
            '123': {
                'traxgen': [['tool: book_flight(departure_date=2024-01-15)', 'tool: check_balance()']]
            },
            '456': {
                'traxgen': [['tool: transfer_funds(amount=100)']]
            }
        }
        
        result = extract_ground_truth_trajectory(ground_truth_data, '123')
        expected = ['tool: book_flight(departure_date=2024-01-15)', 'tool: check_balance()']
        self.assertEqual(result, expected)
        
        result = extract_ground_truth_trajectory(ground_truth_data, 'nonexistent')
        self.assertEqual(result, [])


class TestMetricsFunctions(unittest.TestCase):
    """Test cases for metrics functions from metrics.py"""

    def test_calculate_match_percentage(self):
        """Test match percentage calculation"""
        self.assertEqual(calculate_match_percentage(8, 10), 80.0)
        self.assertEqual(calculate_match_percentage(0, 10), 0.0)
        self.assertEqual(calculate_match_percentage(10, 10), 100.0)
        self.assertEqual(calculate_match_percentage(5, 0), 0.0)  # Division by zero protection

    def test_calculate_param_matches_any_order(self):
        """Test parameter matching calculation"""
        generated = [
            "tool: book_flight(departure_date=2024-01-15, destination=NYC)",
            "tool: check_balance(account=12345)"
        ]
        ground_truth = [
            "tool: book_flight(departure_date=2024-01-15, destination=NYC)",
            "tool: transfer_funds(amount=100, account=12345)"
        ]
        
        matched_params, total_params = calculate_param_matches_any_order(generated, ground_truth)
        # book_flight: departure_date and destination match (2 matches)
        # transfer_funds: no matching tool in generated, so 0 matches
        # Total: 2 matches out of 4 parameters (departure_date, destination, amount, account)
        self.assertEqual(matched_params, 2)  # departure_date, destination
        self.assertEqual(total_params, 4)  # departure_date, destination, amount, account

    def test_compute_3_tool_metrics(self):
        """Test tool metrics computation"""
        predicted = [
            "tool: book_flight(departure_date=2024-01-15)",
            "tool: check_balance()",
            "tool: book_flight(departure_date=2024-01-20)"  # Extra
        ]
        reference = [
            "tool: book_flight(departure_date=2024-01-15)",
            "tool: check_balance()",
            "tool: transfer_funds(amount=100)"  # Missing
        ]
        
        metrics = compute_3_tool_metrics(predicted, reference)
        
        # Precision: 2 correct / 3 predicted = 66.67%
        self.assertAlmostEqual(metrics['precision'], 66.67, places=1)
        # Recall: 2 correct / 3 reference = 66.67%
        self.assertAlmostEqual(metrics['recall'], 66.67, places=1)
        # F1: 2 * 66.67 * 66.67 / (66.67 + 66.67) = 66.67%
        self.assertAlmostEqual(metrics['f1'], 66.67, places=1)

    def test_compare_trajectories(self):
        """Test trajectory comparison"""
        generated = [
            "agent: BasicReActAgent",
            "tool: book_flight(departure_date=2024-01-15, destination=NYC)",
            "agent: OrchestratorAgent",
            "tool: check_balance(account=12345)"
        ]
        ground_truth = [
            "agent: BasicReActAgent", 
            "tool: book_flight(departure_date=2024-01-15, destination=NYC)",
            "agent: OrchestratorAgent",
            "tool: transfer_funds(amount=100, account=12345)"
        ]
        
        metrics = compare_trajectories(generated, ground_truth)
        
        # Check that all expected keys are present
        expected_keys = [
            'exact_match', 'agent_match_percentage_any_order', 'agent_match_percentage_order',
            'lcs_tools', 'tool_precision', 'tool_recall', 'tool_f1_score',
            'fulfillment_tool_precision', 'fulfillment_tool_recall', 'fulfillment_tool_f1_score',
            'param_match_percentage'
        ]
        for key in expected_keys:
            self.assertIn(key, metrics)
        
        # Check specific values
        self.assertFalse(metrics['exact_match'])
        self.assertEqual(metrics['agent_match_percentage_any_order'], 100.0)  # Both agents present
        self.assertEqual(metrics['agent_match_percentage_order'], 100.0)  # Both agents in same order

    def test_compare_fulfillment_tools_non_react(self):
        """Test fulfillment tools comparison for non-react experiments"""
        generated = [
            "agent: OrchestratorAgent",
            "tool: send_verification_text(phone=1234567890)",  # Non-fulfillment
            "agent: UpdateAddressAgent",
            "tool: update_address(zip_code=12345, city=Boston)",  # Fulfillment
            "tool: check_balance()"  # Fulfillment
        ]
        ground_truth = [
            "agent: OrchestratorAgent",
            "tool: send_verification_text(phone=1234567890)",  # Non-fulfillment
            "agent: UpdateAddressAgent",
            "tool: update_address(zip_code=12345, city=Boston)",  # Fulfillment
            "tool: transfer_funds(amount=100)"  # Fulfillment
        ]
        
        metrics = compare_fulfillment_tools(generated, ground_truth)
        
        # Should only consider fulfillment tools (update_address, check_balance vs update_address, transfer_funds)
        # Precision: 1 correct / 2 predicted = 50%
        self.assertEqual(metrics['precision'], 50.0)
        # Recall: 1 correct / 2 reference = 50%
        self.assertEqual(metrics['recall'], 50.0)
        # F1: 2 * 50 * 50 / (50 + 50) = 50%
        self.assertEqual(metrics['f1'], 50.0)

    def test_compare_fulfillment_tools_react(self):
        """Test fulfillment tools comparison for React experiments"""
        generated = [
            "agent: ReActAgent",
            "tool: send_verification_text(phone=1234567890)",  # Non-fulfillment
            "tool: book_flight(departure_date=2024-01-15)",  # Fulfillment
            "tool: code_verifier(code=123456)",  # Non-fulfillment
            "tool: check_balance()"  # Fulfillment
        ]
        ground_truth = [
            "agent: ReActAgent",
            "tool: send_verification_text(phone=1234567890)",  # Non-fulfillment
            "tool: book_flight(departure_date=2024-01-15)",  # Fulfillment
            "tool: code_verifier(code=123456)",  # Non-fulfillment
            "tool: transfer_funds(amount=100)"  # Fulfillment
        ]
        
        metrics = compare_fulfillment_tools(generated, ground_truth)
        
        # Should only consider fulfillment tools (book_flight, check_balance vs book_flight, transfer_funds)
        # Precision: 1 correct / 2 predicted = 50%
        self.assertEqual(metrics['precision'], 50.0)
        # Recall: 1 correct / 2 reference = 50%
        self.assertEqual(metrics['recall'], 50.0)
        # F1: 2 * 50 * 50 / (50 + 50) = 50%
        self.assertEqual(metrics['f1'], 50.0)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""

    def test_empty_inputs(self):
        """Test functions with empty inputs"""
        # Test empty lists
        self.assertEqual(filter_fulfillment_tools([]), [])
        self.assertEqual(extract_agent_tool_sequence([]), [])
        self.assertEqual(count_turns_all([]), 0)
        self.assertEqual(calculate_average_latency([]), 0.0)
        self.assertEqual(count_errors([]), 0)
        
        # Test empty tool lists
        matched_params, total_params = calculate_param_matches_any_order([], [])
        self.assertEqual(matched_params, 0)
        self.assertEqual(total_params, 0)
        
        metrics = compute_3_tool_metrics([], [])
        self.assertEqual(metrics['precision'], 0.0)
        self.assertEqual(metrics['recall'], 0.0)
        self.assertEqual(metrics['f1'], 0.0)

    def test_malformed_data(self):
        """Test functions with malformed data"""
        # Test malformed tool calls
        tool_name, params = parse_tool_call("malformed_tool_call")
        self.assertEqual(tool_name, "malformed_tool_call")
        self.assertEqual(params, {})
        
        # Test malformed JSON
        data = [{"event_type": "tool_called", "data": {"tool_name": "test", "arguments": "invalid_json"}}]
        sequence = extract_agent_tool_sequence(data)
        self.assertIn("tool: test(invalid_json)", sequence)

    def test_file_operations(self):
        """Test file-based operations"""
        # Create temporary JSONL file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"event_type": "user_id", "data": {"id": "test123"}}\n')
            f.write('{"event_type": "tool_called", "data": {"tool_name": "intent_identified", "arguments": "{\\"intent\\": \\"test_intent\\"}"}}\n')
            temp_file = f.name
        
        try:
            user_id, intent = extract_user_intent(temp_file)
            self.assertEqual(user_id, "test123")
            self.assertEqual(intent, "test_intent")
        finally:
            os.unlink(temp_file)


def run_tests():
    """Run all tests and print results"""
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestUtilsFunctions,
        TestMetricsFunctions, 
        TestEdgeCases
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\nFAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print(f"\nERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1) 
import time
import json
from typing import Dict, Any
from agents import TracingProcessor, Trace, Span 
from pydantic import BaseModel 
from agent_setup.setup import Result
import logging
from agents.usage import Usage
from agents import Span
import os


class CustomTracingProcessor(TracingProcessor):
    """
    A custom tracing processor that logs trace and span events, serializes them into JSON, 
    and writes them to a specified output file. Designed to handle complex, non-serializable 
    objects such as sets, callables, and domain-specific classes like Result, Agent, and FunctionTool.
    """
    def __init__(self, output_file: str):
        """
        Initializes the CustomTracingProcessor.

        Args:
            output_file (str): Path to the file where logs should be written.
        """        
        self.output_file = output_file
        self.log_entries = []
    def on_trace_start(self, trace: Trace) -> None:
        """
        Hook that is called when a trace starts.

        Args:
            trace (Trace): The trace object.
        """
        pass
        
    def on_trace_end(self, trace: Trace) -> None:
        """
        Hook that is called when a trace ends.

        Args:
            trace (Trace): The trace object.
        """
        pass
    def on_span_start(self, span: Span) -> None:
        """
        Hook that is called when a span starts.

        Args:
            span (Span): The span object.
        """
        pass

    def on_span_end(self, span: Span) -> None:
        """
        Hook that is called when a span ends.

        Args:
            span (Span): The span object.
        """
        pass

    def shutdown(self) -> None:
        """
        Hook for gracefully shutting down the processor.
        """
        pass

    def force_flush(self) -> None:
        """
        Forces the processor to flush all logs.
        """
        pass

    def log_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Logs an event with the given type and associated data. Handles complex object serialization.

        Args:
            event_type (str): The type or label of the event.
            data (Dict[str, Any]): The data to log. Can contain complex or nested Python objects.
        """

        def convert_sets(value):
            """
            Recursively convert non-serializable objects (e.g., sets, callables, Result, Agent) into serializable formats.
            """
            if isinstance(value, set):
                return list(value)
            elif isinstance(value, dict):
                return {k: convert_sets(v) for k, v in value.items()}
            elif isinstance(value, (list, tuple)):
                return [convert_sets(v) for v in value]
            elif isinstance(value, Result):
                return {k: convert_sets(v) for k, v in value.model_dump().items()}
            elif callable(value):  # Handle function objects
                try:
                    func_name = value.__name__ if hasattr(value, '__name__') else "unknown_function"
                    return f"<function {func_name}>"
                except Exception:
                    return "<callable object>"
            elif hasattr(value, '__class__') and value.__class__.__name__ == 'FunctionTool':
                try:
                    return f"<FunctionTool {value.name}>"
                except Exception:
                    return "<FunctionTool object>"
            # agent objects 
            elif hasattr(value, '__class__') and value.__class__.__name__ == 'Agent':
                try:
                    return f"<Agent {value.name}>"
                except Exception:
                    return "<Agent object>"
            #catch-all for any other non-serializable objects
            elif hasattr(value, '__dict__'):
                try:
                    # try to extract class name and other basic info
                    class_name = value.__class__.__name__
                    return f"<{class_name} object>"
                except Exception:
                    return "<Object>"
            return value
        
        try:
            data_copy = data.copy()
            data_copy = convert_sets(data_copy)
                        
            log_entry = {
                'event_type': event_type,
                'data': data_copy,
                'timestamp': time.time(),
            }
            self.log_entries.append(log_entry)
        except Exception as e:
            print(f"Error serializing log data: {e}")
            # Fallback to a simplified version 
            log_entry = {
                'event_type': event_type,
                'data': {"error": f"Failed to serialize data: {str(e)}"},
                'timestamp': time.time(),
            }
            self.log_entries.append(log_entry)

    def write_logs(self) -> None:
        """
        Writes all accumulated log entries to the output file in JSON lines format, then clears the log buffer.
        """
        with open(self.output_file, "a") as f:
            for entry in self.log_entries:
                f.write(json.dumps(entry) + '\n')
        self.log_entries.clear()



class UsageLogger(TracingProcessor):
    def __init__(self, llm_name: str, experiment_name: str, intent: str):
        self.llm_name = llm_name
        self.experiment_name = experiment_name
        self.usage_output_file = None
        self.cumulative_usage = Usage()
        self.run_wide_log = {}
        self.intent = intent
        self.user_id = None
        self.current_agent = None
        self.span_agent_map = {}


    def on_trace_start(self, trace: Trace) -> None:
        """
        Hook that is called when a trace starts.

        Args:
            trace (Trace): The trace object.
        """
        pass
        
    def on_trace_end(self, trace: Trace) -> None:
        """
        Hook that is called when a trace ends.

        Args:
            trace (Trace): The trace object.
        """
        pass
    def on_span_start(self, span: Span) -> None:
        """
        Hook that is called when a span starts.

        Args:
            span (Span): The span object.
        """
        exported = span.export() or {}
        span_data = exported.get("span_data", {})
        if span_data.get("type") == "agent":
            self.span_agent_map[span.span_id] = span_data.get("name")
            

    def on_span_end(self, span: Span) -> None:
        """
        Hook that is called when a span ends.

        Args:
            span (Span): The span object.
        """
        exported = span.export() or {}
        span_data = exported.get("span_data", {})
        
        usage_dict = getattr(span.span_data, "usage", None)
        if not usage_dict:
            exported = span.export() or {}
            usage_dict = exported.get("span_data", {}).get("usage")

        if not isinstance(usage_dict, dict):
            return

        inp = usage_dict.get("input_tokens", 0)
        out = usage_dict.get("output_tokens", 0)
        total = inp+out
        call_usage = Usage(
            requests=1,
            input_tokens=inp,
            output_tokens=out,
            total_tokens=total,
        )

        print(f"[LLM] prompt={inp}  completion={out}  total={total}")
        self.cumulative_usage.add(call_usage)
        print(
            f"[LLM cumulative] requests={self.cumulative_usage.requests}, "
            f"tokens={self.cumulative_usage.total_tokens}"
        )
        #######Detect inlined function calls inside generation spans
        tool_calls = None
        if span_data.get("type") == "generation":
            for out_entry in span_data.get("output", []):
                calls = out_entry.get("tool_calls")
                if calls:
                    tool_calls = calls
                    break

        ####### Span parsing #######
        span_type = span_data.get("type")
        function_name = None
        call_type = None

        # inline function call in generation
        if tool_calls:
            call_type = "function_call"
            function_name = tool_calls[0]["function"]["name"]

        elif span_type == "generation":
            call_type = "text_generation"

        elif span_type == "function":
            call_type = "function_call"
            function_name = span_data.get("name")

        elif span_type == "handoff":
            call_type = "handoff"

        else:
            call_type = span_type
            
        ####### Agent resolution #######
        agent = self.span_agent_map.get(span.span_id)
        if agent is None and span.parent_id:
            agent = self.span_agent_map.get(span.parent_id)
            
        ####### Log entry composition #######
        log_entry = {
            "client_id": self.user_id,
            "agent": agent,
            "type": call_type,
            "function_name": function_name,
            "prompt_tokens": inp,
            "completion_tokens": out,
            "total_tokens": total,
        }
        os.makedirs(os.path.dirname(self.usage_output_file), exist_ok=True)

        # write to file immediately (append)
        with open(self.usage_output_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, default=str) + "\n")

        # still keep it in memory if needed
        if self.user_id not in self.run_wide_log:
            self.run_wide_log[self.user_id] = []

    def set_user_id(self, user_id: str):
        ## fresh count for new user
        if user_id != self.user_id:
            self.cumulative_usage = Usage()
            
        self.user_id = user_id
        parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        self.usage_output_file = os.path.join(
            parent_dir, "output", "usage",
            self.llm_name,
            self.experiment_name,
            self.intent,
            f"{user_id}.jsonl"
        )
        
        output_dir = os.path.dirname(self.usage_output_file)
        os.makedirs(output_dir, exist_ok=True)
    
    def shutdown(self) -> None:
        """
        Hook for gracefully shutting down the processor.
        """
        pass

    def force_flush(self) -> None:
        """
        Forces the processor to flush all logs.
        """
        pass

    def log_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Logs an event with the given type and associated data. Handles complex object serialization.

        Args:
            event_type (str): The type or label of the event.
            data (Dict[str, Any]): The data to log. Can contain complex or nested Python objects.
        """
        pass

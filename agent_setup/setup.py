from dotenv import load_dotenv
import os
import sys
import numpy as np
import pandas as pd
from pydantic import BaseModel, SkipValidation
from typing import Dict, List, Any, Union
import importlib
import time
from agents import Agent, Runner, function_tool, ModelSettings, handoff
from agents.extensions.models.litellm_model import LitellmModel
import json
from models import AuthenticatedCustomerContext

# 1) read from the environment
MODEL_NAME = os.environ.get("AGENT_MODEL", "gpt-4o")
API_KEY = os.environ.get("AGENT_API_KEY", "")
PROMPT = os.environ.get("PROMPT", "")

# else:
MODEL_BACKEND = LitellmModel(      
    model=MODEL_NAME,
    api_key=API_KEY
)

# Agent_setup imports
# from agent_setup.models import fulfillment_model, orchestrator_model, personalizer_model, authenticator_model
from agent_setup.instructions import personalizer_instructions, authenticator_instructions, fulfillment_agent_intro, extra_orchestrator_instruction_for_llama, extra_authenticator_instruction_for_llama

# Local imports (e.g., handoff and orchestrator tools)
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import DOMAIN_TOOLS_MAPPING, CLIENT_INFO_TOOLS_MAPPING, ROUTINE_MAPPING


## Instantiating Results Class 

class Result(BaseModel):
    """
    A model that represents the result of a tool call, typically used to indicate success or failure.
    
    Attributes:
        value (str): A string representing the result of the operation.
        agent (SkipValidation): The next agent that it should be transferred to.
    """
    value: str = ''
    agent: SkipValidation
    class Config:
        arbitrary_types_allowed = True 


def get_orchestrator_instructions(domain: str) -> str:
    """
    Generate domain-specific instructions for the orchestrator agent.

    Args:
        domain (str): The domain (e.g., 'Flights', 'Hospital') for which the orchestrator agent instructions are generated.

    Returns:
        str: The instructions for the orchestrator agent in the specified domain, including available intents and steps to follow.
        None: If there is an error loading the intent mapping for the given domain.
    """
    try:
        # Import the intent mapping for the domain
        folder_domain = None
        if domain.capitalize() == 'Banking':
            folder_domain = 'SimpleBanking'
        elif domain.capitalize() == 'Flights':
            folder_domain = 'IntermediateFlights'
        elif domain.capitalize() == 'Hospital':
            folder_domain = 'ComplexHospital'

            
        mapping_module = importlib.import_module(f'test_data.{folder_domain}.intent_mapping')
        intent_mapping = getattr(mapping_module, 'INTENT_MAPPING')
        
        # Get all available intents for this domain
        available_intents = [config['intent'] for config in intent_mapping.values()]
        intents_str = ", ".join(available_intents)

        return f"""{RECOMMENDED_PROMPT_PREFIX}
         You are a customer service representative for the {domain} domain. Your role is to determine the client's intent and direct them to the appropriate agent.

         The only available intents for {domain} are:
         {intents_str} 

         Steps:
         1) If the client's intent isn't clear, ask questions to disambiguate. 
         2) Once you know the intent, ALWAYS CALL the intent_identified(intent, domain='{domain}') tool with both the intent and domain parameters.
         3) Handoff: After calling intent_identified, simply acknowledge the intent has been identified and immediately hand off to the authenticator agent. Do NOT attempt to execute any tools or routines mentioned in the response.

         Important:
         - Only handle intents listed above. Anything else is out of scope.
         - If the client's request doesn't match any available intent, politely explain which services you can help with.
         - Always include the domain parameter when calling intent_identified.
         - You are ONLY responsible for intent identification - do not attempt to execute any domain-specific tools or routines.
         """
    except Exception as e:
        print(f"Error loading intent mapping for domain {domain}: {e}")
        return None

def get_fulfillment_instructions(customer_id: int) -> str:
    """
    Generate instructions for the fulfillment agent.

    Args:
        customer_id (int): The customer ID for which fulfillment instructions are generated.

    Returns:
        str: The instructions for the fulfillment agent specific to the given customer ID.
    """
    return f" The fulfillment agent will take care of this customer with customer ID {customer_id}. {fulfillment_agent_intro}"


@function_tool
async def intent_identified(intent: str, domain: str) -> Dict:
    """
    Function to call when the intent has been identified.

    Args:
        intent (str): The identified intent.
        domain (str): The domain for the intent (e.g., 'Flights', 'Hospital').

    Returns:
        dict: A dictionary containing routine and tools associated with the identified intent, including 'intent', 'routine', 'info_gathering_tools', and 'execution_tools'.
    """
    try:
        execution_tools = DOMAIN_TOOLS_MAPPING[intent]
        client_info_tools = CLIENT_INFO_TOOLS_MAPPING[intent]
        routine = ROUTINE_MAPPING[intent]

        return {
            'intent': intent, 
            "routine": routine,
            "info_gathering_tools": client_info_tools,
            "execution_tools": execution_tools,
            "message": f"Intent '{intent}' has been successfully identified for the {domain} domain. Please proceed with customer authentication - the specialized fulfillment agent will handle the detailed execution after authentication is complete."
            }
        
    except Exception as e:
        import traceback
        print(f"Error in intent_identified: {str(e)}")
        print(traceback.format_exc())
        return {"error": f"Error loading intent configuration: {str(e)}"}


@function_tool
def send_verification_text(phone_number: int):
    """
    Simulate sending a verification text to the provided phone number.

    Args:
        phone_number (int): The client's phone number for sending the verification code.

    Returns:
        str: A message indicating that the verification message has been sent to the phone number.
    """
    print(f"Sending verification text to {phone_number}...")
    time.sleep(6) #adding 6 seconds to allow for client to find message.
    return f"A verification message has been sent to your phone number. You should receive it shortly."



@function_tool
def code_verifier(code: Union[int, str], customer_id: int):
    """
    Verify if the code provided by the client matches the correct code.
    
    Args:
        code (Union[int, str]): The verification code entered by the client.
        customer_id (str): The customer ID of the client.
   
    Returns:
    - A Result object with verification result and the assigned agent.
    """
    verification_result = True
    print("The code has been verified")
    time.sleep(5)
    fulfillment_agent = setup_fulfillment_agent(customer_id)
    result = Result(
        value = "Code verified successfully" if verification_result else "Verification failed",
        agent = fulfillment_agent  
    )
    return result


def setup_fulfillment_agent(customer_id: int) -> Agent:
    """
    Set up the fulfillment agent for handling the intent completion after authentication.

    Args:
        customer_id (str): The customer ID for which the fulfillment agent is set up.

    Returns:
        Agent: The fulfillment agent with necessary instructions and tools.
    """
    instructions = get_fulfillment_instructions(customer_id)
            
    return Agent(
        name="FulfillmentAgent",
        handoff_description = "Specialist Agent that will take care of the intent completion after the authentication has been finalized.",
        instructions=instructions,
        tools=[],
        model=MODEL_BACKEND
    )


def setup_orchestrator_agent(domain: str, customer_id: int) -> Agent:
    """
    Set up the orchestrator agent to use domain-specific instructions and handoff to the authenticator agent.

    Args:
        domain (str): The domain for which the orchestrator agent is being set up.
        customer_id (str): The customer ID for the authenticator agent.

    Returns:
        Agent: The orchestrator agent with appropriate instructions and handoff setup.

    Raises:
        ValueError: If instructions for the domain cannot be generated.
    """
    instructions = get_orchestrator_instructions(domain)
    
    if not instructions:
        raise ValueError(f"Failed to generate instructions for domain: {domain}")
        
    if "llama" in MODEL_NAME:
        instructions += extra_orchestrator_instruction_for_llama    
        
    authenticator_agent = setup_authenticator_agent(customer_id)

    return Agent(
        name="OrchestratorAgent",
        instructions=instructions,
        handoffs = [authenticator_agent],
        tools=[intent_identified],
        model=MODEL_BACKEND 
    )


### Setting up the Personalizer Agent
def setup_personalizer_agent() -> Agent:
    
    personalizer_agent = Agent(name="PersonalizerAgent",
                handoff_description = "Specialist Agent that personalizes standard routines for each client based on their data",
                instructions = personalizer_instructions,
                model = MODEL_BACKEND)  

    return personalizer_agent


def get_authenticator_instructions(customer_id: int) -> str:
    """
    Generate instructions for the authenticator agent.

    Args:
        customer_id (str): The customer ID for which authenticator instructions are generated.

    Returns:
        str: The instructions for the authenticator agent specific to the given customer ID.
    """
    return f"The customer you are authenticating has customer ID: {customer_id}. {authenticator_instructions}"


def setup_authenticator_agent(customer_id: int) -> Agent:
    """
    Set up the authenticator agent for verifying customer information.

    Args:
        customer_id (str): The customer ID for which the authenticator agent is set up.

    Returns:
        Agent: The authenticator agent with appropriate tools and instructions.
    """
    instructions = get_authenticator_instructions(customer_id)
    if "llama" in MODEL_NAME:
        instructions += extra_authenticator_instruction_for_llama
        
    return Agent(
            name="AuthenticatorAgent",
            instructions=instructions,
            tools=[send_verification_text, code_verifier], 
            model=MODEL_BACKEND 
        )

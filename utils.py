import ast
import os
import re
import importlib
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel
import aiofiles
from agents import Agent, function_tool

############# SimpleBanking - Tools #############
from test_data.SimpleBanking.update_address.full_tools import (
    get_account_type,
    get_account_type_extra,
    update_address,
    apply_address_hold,
    validate_address,
)
from test_data.SimpleBanking.withdraw_retirement_funds.full_tools import (
    check_withdrawal_eligibility,
    check_withdrawal_eligibility_extra,
    process_retirement_withdrawal,
)

############# SimpleBanking - Routines #############
from test_data.SimpleBanking.update_address.full_workflow import update_address_workflow
from test_data.SimpleBanking.withdraw_retirement_funds.full_workflow import withdraw_retirement_funds_workflow

############# Flights - Tools #############
from test_data.IntermediateFlights.book_flight.full_tools import (
    check_visa_requirements,
    create_booking,
    create_booking_with_points,
    get_customer_frequent_flyer_status,
    get_customer_frequent_flyer_status_extra,
    get_customer_payment_method,
    get_customer_payment_method_extra,
    get_passport_info,
    get_passport_info_extra,
    search_priority_flights,
    search_regular_flights,
)
from test_data.IntermediateFlights.cancel_flight.full_tools import (
    calculate_cancellation_fee,
    cancel_flight,
    get_booking_details,
    get_booking_details_extra,
    get_customer_loyalty_info,
    get_customer_loyalty_info_extra,
    issue_travel_credit,
    process_refund,
    check_cancellation_blockers
)

############# Flights - Routines #############
from test_data.IntermediateFlights.book_flight.full_workflow import book_flight_workflow
from test_data.IntermediateFlights.cancel_flight.full_workflow import cancel_flight_workflow

############# Hospital - Tools #############
from test_data.ComplexHospital.book_appointment.full_tools import (
    book_appointment,
    check_if_customer_has_referral,
    check_if_customer_has_referral_extra,
    find_available_appointments,
    get_patient_profile_extra,
    get_patient_demographics,
    get_patient_demographics_extra,
    get_medical_history_summary,
    get_medical_history_summary_extra,
    get_emergency_contact,
    get_emergency_contact_extra,
    get_insurance_coverage_details,
    get_insurance_coverage_details_extra,
    collect_emergency_contact,
    route_to_specialist,
    route_to_financial_support,
    assign_language_support,
    set_guardian_contact,
    suggest_accessible_hospitals,
    get_hospital_bed_availability_api,
    get_provider_contact_info_api,
    check_appointment_conflict_live_api,
    suggest_nearest_hospital,
    check_insurance_plan_validity,
    suggest_appointment_type,
    set_up_reminder,
)
from test_data.ComplexHospital.process_payment.full_tools import (
    calculate_patient_responsibility,
    get_insurance_payment_portion,
    get_billing_info,
    get_billing_info_extra,
    check_account_status,
    check_account_status_extra,
    evaluate_payment_urgency,
    evaluate_payment_urgency_extra,
    calculate_late_fee_waiver_eligibility,
    calculate_late_fee_waiver_eligibility_extra,
    get_provider_contact_info_api,
    apply_fee_waiver,
    currency_exchange,
    run_fraud_check,
    get_hospital_contact_info,
    initiate_3ds_auth,
    initiate_ach_transaction,
    get_wallet_link,
    check_wallet_payment_status,
    process_payment,
    setup_payment_plan,
    issue_receipt,
)

############# Hospital - Routines #############
from test_data.ComplexHospital.book_appointment.full_workflow import book_appointment_workflow
from test_data.ComplexHospital.process_payment.full_workflow import process_payment_workflow


@function_tool
async def complete_case(customer_id: int) -> Dict:
    '''
    Closes the case and logs the interaction
    
    Args:
        customer_id: ID of the customer
    Returns:
        Dict indicating success
    '''
    # Simulate case completion
    return {
        'success': True,
        'message': 'Case completed successfully',
        'customer_id': customer_id
    }
    

DOMAIN_TOOLS_MAPPING = {
    "update_address": [
        validate_address,
        update_address,
        apply_address_hold,
        complete_case
    ],
    "withdraw_retirement_funds": [
        process_retirement_withdrawal,
        complete_case
    ],
    "cancel_flight": [
        check_cancellation_blockers,
        calculate_cancellation_fee,
        cancel_flight,
        process_refund,
        issue_travel_credit,
        complete_case
    ],
    "book_flight": [
        search_regular_flights,
        search_priority_flights,
        check_visa_requirements,
        create_booking,
        create_booking_with_points,
        complete_case,
    ],
    "book_appointment": [
        find_available_appointments,
        book_appointment,
        set_up_reminder,
        get_hospital_bed_availability_api,
        get_provider_contact_info_api,
        check_appointment_conflict_live_api,
        suggest_nearest_hospital,
        check_insurance_plan_validity,
        suggest_appointment_type,
        collect_emergency_contact,
        route_to_specialist,
        route_to_financial_support,
        assign_language_support,
        set_guardian_contact,
        suggest_accessible_hospitals,
        complete_case
    ],
    "process_payment": [
        get_insurance_payment_portion,
        calculate_patient_responsibility,
        apply_fee_waiver,
        get_provider_contact_info_api,
        currency_exchange,
        run_fraud_check,
        get_hospital_contact_info,
        initiate_3ds_auth,
        initiate_ach_transaction,
        get_wallet_link,
        check_wallet_payment_status,
        process_payment,
        issue_receipt,
        setup_payment_plan,
        complete_case
    ]
}

CLIENT_INFO_TOOLS_MAPPING = {
    "update_address": [
        get_account_type,
    ],
    "withdraw_retirement_funds": [
        check_withdrawal_eligibility
    ],
    "cancel_flight": [
        get_booking_details,
        get_customer_loyalty_info
    ],
    "book_flight": [
        get_customer_frequent_flyer_status,
        get_passport_info,
        get_customer_payment_method
    ],
    "book_appointment": [
        get_patient_demographics,
        get_insurance_coverage_details,
        get_medical_history_summary,
        check_if_customer_has_referral,
        get_emergency_contact
    ],
    "process_payment": [
        get_billing_info,
        check_account_status,
        evaluate_payment_urgency,
        calculate_late_fee_waiver_eligibility
    ]
}

CLIENT_INFO_TOOLS_EXTRA_MAPPING = {
    "update_address": [
        get_account_type_extra,
    ],
    "withdraw_retirement_funds": [
        check_withdrawal_eligibility_extra
    ],
    "cancel_flight": [
        get_booking_details_extra,
        get_customer_loyalty_info_extra
    ],
    "book_flight": [
        get_customer_frequent_flyer_status_extra,
        get_passport_info_extra,
        get_customer_payment_method_extra
    ],
    "book_appointment": [
        get_patient_profile_extra,
        get_patient_demographics_extra,
        get_insurance_coverage_details_extra,
        get_medical_history_summary_extra,
        check_if_customer_has_referral_extra,
        get_emergency_contact_extra
    ],
    "process_payment": [
        get_billing_info_extra,
        check_account_status_extra,
        evaluate_payment_urgency_extra,
        calculate_late_fee_waiver_eligibility_extra
    ]
}

ALL_TOOL_MAPPING = {} 

for intent in DOMAIN_TOOLS_MAPPING:
    ALL_TOOL_MAPPING[intent] = CLIENT_INFO_TOOLS_EXTRA_MAPPING[intent] + DOMAIN_TOOLS_MAPPING[intent] 


ROUTINE_MAPPING = {
    "update_address": update_address_workflow,
    "withdraw_retirement_funds": withdraw_retirement_funds_workflow,
    "cancel_flight": cancel_flight_workflow,
    "book_flight": book_flight_workflow,
    "book_appointment": book_appointment_workflow,
    "process_payment": process_payment_workflow
}

def new_handle_agent_handoff(current_agent, context, intent_identified, intent_personalized_routine, available_tools, intent_full_routine, intent_all_tools, parallelization = True):
    """
    Function to handle agent handoff and update relevant parameters.
    It updates the last agent parameters and assigns the relevant tools.

    Arguments:
    - current_agent: The current agent to be updated
    - context: The context object containing personalized routines and tools
    - parallelization: Boolean to determine which routine to use

    Returns:
    - Updated agent with instructions and tools.
    """
    try:
        current_agent.name = intent_identified  # Fulfillment agent name
        if parallelization:
            current_agent.instructions += intent_personalized_routine
            current_agent.tools = available_tools
            print("*"*100)
            print(available_tools)
        else:
            current_agent.instructions += intent_full_routine
            current_agent.tools = intent_all_tools

    except Exception as e:
        import traceback
        print(f"Error setting up agent tools: {str(e)}")
        print(traceback.format_exc())
        current_agent.tools = None


def extract_tools(routine):
    """
    Extracts the list of tools from a routine string by parsing the assignment 
    to the variable 'available_tools'.

    Parameters:
    - routine (str): The routine as a string containing a line like 
      'available_tools = [tool1, tool2, ...]'.

    Returns:
    - list: A list of tools if found, otherwise an empty list.
    """
    match = re.search(r"available_tools\s*=\s*(\[[^\]]*\])", routine)
    return ast.literal_eval(match.group(1)) if match else []


async def save_routine_async(filepath, content):
    """
    Asynchronously saves a string content to a specified file inside the 
    'evaluation/trimmed_routines' directory.

    Parameters:
    - filename (str): The name of the file to save the content in.
    - content (str): The text content to write to the file.

    Side Effects:
    - Creates directories as needed.
    - Writes the file asynchronously.
    - Prints a success or error message to the console.
    """
    try:
        async with aiofiles.open(filepath, "w", encoding="utf-8") as file:
            await file.write(content)
        
        print(f"\033[32mRoutine saved asynchronously to {filepath}\033[0m")
    except Exception as e:
        print(f"\033[91mError saving routine asynchronously: {e}\033[0m")



def on_llm_end_hook(*, usage, **kwargs):
    print("[HOOK] on_llm_end_hook was triggered")
    print(f"[LLM] prompt={usage.input_tokens}  completion={usage.output_tokens}  total={usage.total_tokens}")
    usage_logger.cumulative_usage.add(usage)

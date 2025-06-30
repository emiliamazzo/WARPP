import random
from models import AuthenticatedCustomerContext
from typing import Dict
import json
from agents import function_tool
import os
import requests
import http.client

customer_data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'test_data', 'customer_data', 'hospital_utterance.json')
with open(customer_data_path, 'r') as f:
    customer_data = json.load(f)
    
    
###########################################################
######## CLIENT INFO TOOLS############################
###########################################################

async def get_patient_profile(context: AuthenticatedCustomerContext) -> Dict:
    '''
    Retrieves the full patient profile, including demographics,
    insurance, medical info, communication prefs, emergency contact,
    and coverage details if present.

    Args:
        context: The authenticated customer context containing the customer's ID.
    Returns:
        Dict: {
            patient_info: Dict,
            medical_info: Dict,
            outstanding_blance: float,
            payment_plan_active: bool,
            communication_preferences: Dict,
            emergency_contact: Dict,
            insurance_coverage_details: Dict
        }
    '''
    for patient in customer_data:
        if patient['customer_id'] == context.customer_id:
            billing_info = patient.get('billing_info', {})
            return {
                'patient_info': patient.get('patient_info', {}),
                'medical_info': patient.get('medical_info', {}),
                'outstanding_balance': billing_info['outstanding_balance'],
                'payment_plan_active': billing_info['payment_plan_active'],
                'communication_preferences': patient.get('communication_preferences', {}),
                'emergency_contact': patient.get('emergency_contact', {}),
                'insurance_coverage_details': patient.get('insurance_coverage_details', {})
            }
    # fallback empty structure
    return {
        'patient_info': {},
        'medical_info': {},
        'communication_preferences': {},
        'emergency_contact': {},
        'insurance_coverage_details': {}
    }

async def get_medical_history_summary(context: AuthenticatedCustomerContext) -> Dict:
    '''
    Retrieves medical history summary, including critical conditions.

    Args:
        context: The authenticated customer context containing the customer's ID.
    Returns:
        Dict: {critical_conditions: List[str] }
    '''
    for patient in customer_data:
        if patient['customer_id'] == context.customer_id:
            history = patient.get('medical_info', {})
            return {
                'critical_conditions': history.get('critical_conditions', [])
            }
    return {
        'critical_conditions': []
    }
    

async def get_emergency_contact(context: AuthenticatedCustomerContext) -> Dict:
    '''
    Retrieves emergency contact details.

    Args:
        context: The authenticated customer context containing the customer's ID.
    Returns:
        Dict: { name: str or None, email: str or None }
    '''
    for patient in customer_data:
        if patient['customer_id'] == context.customer_id:
            contact = patient.get('emergency_contact', {})
            return {
                'name': contact.get('name'),
                'email': contact.get('email')
            }
    return {
        'name': None,
        'email': None
    }

async def get_patient_demographics(context: AuthenticatedCustomerContext) -> Dict:
    '''
    Retrieves patient demographics including age, language preference, and mobility status.
    
    Args:
        context: The authenticated customer context containing the customer's ID.
    Returns:
        Dict: {
            age: int or None,
            language_preference: str or None,
        }
    '''
    for patient in customer_data:
        if patient['customer_id'] == context.customer_id:
            patient_info = patient.get('patient_info', {})
            return {
                "age": patient_info.get('age'),
                "language_preference": patient_info.get('language_preference'),
            }
    # fallback if customer not found
    return {
        "age": None,
        "language_preference": None,
    }

async def check_if_customer_has_referral(context: AuthenticatedCustomerContext) -> Dict:
    '''
    Checks if the customer already has a referral for this appointment or not.
    
    Args:
        context: The authenticated customer context containing the customer's ID.
    Returns:
        Dict: Dict indicating if referral is required
    '''
    for patient in customer_data:
        if patient['customer_id'] == context.customer_id:
            referral_info = patient.get('referral_info', {})
            return {'has_referral': referral_info.get('has_referral', False)}
    
    # fallback if customer not found
    return {'has_referral': False}

    
async def get_insurance_coverage_details(context: AuthenticatedCustomerContext) -> Dict:
    '''
    Retrieves coverage limits and out-of-pocket maximum for the customer.

    Args:
        context: The authenticated customer context containing the customer's ID.
    Returns:
        Dict: { coverage_limits: Dict[str, float], out_of_pocket_max: float }
    '''
    for patient in customer_data:
        if patient['customer_id'] == context.customer_id:
            coverage = patient.get('insurance_coverage_details', {})
            return {
                'coverage_limits': coverage.get('coverage_limits', {}),
                'out_of_pocket_max': coverage.get('out_of_pocket_max', 0.0)
            }
    return {
        'coverage_limits': {},
        'out_of_pocket_max': 0.0
    }
    
###########################################################
######## EXECUTION TOOLS############################
###########################################################
@function_tool
async def find_available_appointments(customer_id: int) -> Dict:
    '''
    Finds providers available for requested specialty
    
    Args:
        customer_id: Customer's ID
    Returns:
        Dict: Dict including available providers
    '''
    # Simulate finding available providers
    return {'appointment_available': 'We have found an appointment for you!'}


@function_tool
async def book_appointment(customer_id: int) -> Dict:
    '''
    Books the appointment in the system
    
    Args:
        customer_id: Customer's ID
    Returns:
        Dict: Dict confirming the appointment booking
    '''
    # Simulate booking appointment
    return {'appointmentBooked': True}


@function_tool
async def set_up_reminder(customer_id: int) -> Dict:
    '''
    Sets up a reminder for the patient
    
    Args:
        customer_id: ID of the customer/patient
    Returns:
        Dict: Dict confirming that the reminder has been set
    '''
    # Simulate setting up reminder (this could be extended to include actual reminder logic)
    return {
        'reminderSet': True,
        'message': f"Reminder has been successfully set for customer {customer_id}."
    }

@function_tool
async def get_hospital_bed_availability_api(hospital_id: int) -> Dict:
    """
    Simulates querying hospital bed availability from the US Hospitals RapidAPI.

    Args:
        hospital_id: Random integer between 110000 and 700000.

    Returns:
        Dict with number of available beds.
    """


    conn = http.client.HTTPSConnection("us-hospitals.p.rapidapi.com")

    headers = {
        'x-rapidapi-key': "c2812472bamshabd9cfa9f3b6258p14b422jsn655e65eaefec",
        'x-rapidapi-host': "us-hospitals.p.rapidapi.com"
    }

    conn.request("GET", f"/?ccn={hospital_id}", headers=headers)

    res = conn.getresponse()
    data = res.read()

    # print(data.decode("utf-8"))
    return {data[0]}


@function_tool
async def get_provider_contact_info_api(provider_id: str) -> Dict:
    """
    Simulates fetching provider contact info from the US Doctors API.

    Args:
        provider_id: String representing provider's unique ID.

    Returns:
        Dict with provider business address and phone number.
    """


    conn = http.client.HTTPSConnection("us-doctors-and-medical-professionals.p.rapidapi.com")

    headers = {
        'x-rapidapi-key': "c2812472bamshabd9cfa9f3b6258p14b422jsn655e65eaefec",
        'x-rapidapi-host': "us-doctors-and-medical-professionals.p.rapidapi.com"
    }

    conn.request("GET", f"/search_npi?npi={provider_id}", headers=headers)

    res = conn.getresponse()
    data = res.read()

    print(data.decode("utf-8"))
    # print(data)
    if data['Code'] == 200:
        return {
            "phone": data['Data']['phone']
        }
    else:
        return {
            "phone": "No phone number found"
        }
    
    
@function_tool
async def check_appointment_conflict_live_api(customer_id: int, preferred_date: str) -> Dict:
    """
    Simulates a check for time conflicts in the patient's appointment calendar.
    """
    conflict = False
    return {
        "hasConflict": conflict}


@function_tool
async def suggest_nearest_hospital(zip_code: str) -> Dict:
    """
    Suggests nearest hospital based on ZIP code.
    """
    hospitals = [
        {"name": "Mercy General", "distance": "2.1 miles"},
        {"name": "St. Luke's", "distance": "4.7 miles"},
    ]
    return {"suggestedHospitals": hospitals}



@function_tool
async def check_insurance_plan_validity(customer_id: int) -> Dict:
    """
    Checks whether the customer's insurance plan is active.
    """
    valid = random.choices([True, False], weights=[0.9, 0.1], k=1)[0]
    return {
        "isValid": valid,
        "message": "Your insurance plan is active." if valid else "Your insurance plan has expired."
    }

@function_tool
async def suggest_appointment_type(symptom_description: str) -> Dict:
    """
    Suggests appointment types based on user symptoms.
    """
    # Simulate classification
    if "chest pain" in symptom_description.lower():
        return {"suggested_type": "Cardiology"}
    elif "rash" in symptom_description.lower():
        return {"suggested_type": "Dermatology"}
    return {"suggested_type": "General Consultation"}


@function_tool
async def collect_emergency_contact(customer_id: int) -> Dict:
    '''
    Collects emergency contact from user (stub for now).

    Args:
        customer_id: ID of the customer/patient
    Returns:
        Dict: Confirmed emergency contact
    '''
    for patient in customer_data:
        if patient['customer_id'] == customer_id:
            patient['emergency_contact'] = {
                'name': 'John Doe',
                'phone': '555-123-4567'
            }
            return patient['emergency_contact']
    return {
        'name': 'John Doe',
        'phone': '555-123-4567'
    }


@function_tool
async def route_to_specialist(customer_id: int) -> Dict:
    '''
    Routes the patient to a specialist based on critical conditions.

    Args:
        customer_id: ID of the customer/patient
    Returns:
        Dict: Confirmation of routing
    '''
    # In practice, this would interact with a scheduling or triage system
    return {
        'status': 'routed',
        'message': f'Customer {customer_id} has been routed to a specialist.'
    }


@function_tool
async def route_to_financial_support(customer_id: int) -> Dict:
    '''
    Routes the patient to financial counseling or support services.

    Args:
        customer_id: ID of the customer/patient
    Returns:
        Dict: Confirmation of routing
    '''
    return {
        'status': 'routed',
        'message': f'Customer {customer_id} has been routed to financial support.'
    }


@function_tool
async def assign_language_support(customer_id: int, language: str) -> Dict:
    '''
    Assigns a support agent for non-English speaking patients.
    
    Args:
        customer_id: ID of the customer/patient
        language: Language code for support assignment
    Returns:
        Dict: Confirmation of language support assignment
    '''
    return {"assigned": True, "language": language}


@function_tool
async def set_guardian_contact(customer_id: int) -> Dict:
    '''
    Sets guardian contact information for patients who are minors.
    
    Args:
        customer_id: ID of the customer/patient
    Returns:
        Dict: {
            guardian_name: str,
            relationship: str,
            phone: str
        }
    '''
    for patient in customer_data:
        if patient['customer_id'] == customer_id:
            patient['guardian_contact'] = {
                'guardian_name': 'John Doe',
                'relationship': 'Parent',
                'phone': '555-987-6543'
            }
            return patient['guardian_contact']
    
    # fallback if customer not found
    guardian_info = {
        'guardian_name': 'John Doe',
        'relationship': 'Parent',
        'phone': '555-987-6543'
    }
    return guardian_info


@function_tool
async def suggest_accessible_hospitals(customer_id: int) -> Dict:
    '''
    Suggests hospitals with accessibility support for patients with mobility issues.
    
    Args:
        customer_id: ID of the customer/patient
    Returns:
        Dict: {
            hospitals: List[Dict] with name and distance information
        }
    '''
    return {
        "hospitals": [
            {"name": "CityMed Rehab", "distance": "2.4 miles"},
            {"name": "Hope Accessible Care", "distance": "3.1 miles"}
        ]
    }




###########################################################
######## CLIENT EXTRA TOOLS############################
###########################################################
@function_tool
async def get_patient_profile_extra(customer_id: int) -> Dict:
    '''
    Retrieves the full patient profile, including demographics,
    insurance, medical info, communication prefs, emergency contact,
    and coverage details if present.

    Args:
        customer_id: ID of the customer/patient
    Returns:
        Dict: {
            patient_info: Dict,
            medical_info: Dict,
            outstanding_blance: float,
            payment_plan_active: bool,
            communication_preferences: Dict,
            emergency_contact: Dict,
            insurance_coverage_details: Dict
        }
    '''
    for patient in customer_data:
        if patient['customer_id'] == customer_id:
            return {
                'patient_info': patient.get('patient_info', {}),
                'medical_info': patient.get('medical_info', {}),
                'outstanding_balance': billing_info['outstanding_balance'],
                'payment_plan_active': billing_info['payment_plan_active'],
                'communication_preferences': patient.get('communication_preferences', {}),
                'emergency_contact': patient.get('emergency_contact', {}),
                'insurance_coverage_details': patient.get('insurance_coverage_details', {})
            }
    # fallback empty structure
    return {
        'patient_info': {},
        'medical_info': {},
        'communication_preferences': {},
        'emergency_contact': {},
        'insurance_coverage_details': {}
    }

@function_tool
async def get_medical_history_summary_extra(customer_id: int) -> Dict:
    '''
    Retrieves medical history summary, including critical conditions.

    Args:
        customer_id: ID of the customer/patient
    Returns:
        Dict: { critical_conditions: List[str] }
    '''
    for patient in customer_data:
        if patient['customer_id'] == customer_id:
            history = patient.get('medical_info', {})
            return {
                'critical_conditions': history.get('critical_conditions', [])
            }
    return {
        'critical_conditions': []
    }


@function_tool
async def get_emergency_contact_extra(customer_id: int) -> Dict:
    '''
    Retrieves emergency contact details.

    Args:
        customer_id: ID of the customer/patient
    Returns:
        Dict: { name: str or None, email: str or None }
    '''
    for patient in customer_data:
        if patient['customer_id'] == customer_id:
            contact = patient.get('emergency_contact', {})
            return {
                'name': contact.get('name'),
                'email': contact.get('email')
            }
    return {
        'name': None,
        'email': None
    }

@function_tool
async def get_patient_demographics_extra(customer_id: int) -> Dict:
    '''
    Retrieves patient demographics including age, language preference, and mobility status.
    
    Args:
        customer_id: ID of the customer/patient
    Returns:
        Dict: {
            age: int or None,
            language_preference: str or None,
        }
    '''
    for patient in customer_data:
        if patient['customer_id'] == customer_id:
            patient_info = patient.get('patient_info', {})
            return {
                "age": patient_info.get('age'),
                "language_preference": patient_info.get('language_preference'),
            }
    # fallback if customer not found
    return {
        "age": None,
        "language_preference": None,
    }


@function_tool
async def check_if_customer_has_referral_extra(customer_id: int) -> Dict:
    '''
    Checks if the customer already has a referral for this appointment or not.
    
    Args:
        customer_id: ID of the customer/patient
    Returns:
        Dict: Dict indicating if referral is required
    '''
    for patient in customer_data:
        if patient['customer_id'] == customer_id:
            referral_info = patient.get('referral_info', {})
            return {'has_referral': referral_info.get('has_referral', False)}
    
    # fallback if customer not found
    return {'has_referral': False}

@function_tool
async def get_insurance_coverage_details_extra(customer_id: int) -> Dict:
    '''
    Retrieves coverage limits and out-of-pocket maximum for the customer.

    Args:
        customer_id: ID of the customer/patient
    Returns:
        Dict: { coverage_limits: Dict[str, float], out_of_pocket_max: float }
    '''
    for patient in customer_data:
        if patient['customer_id'] == customer_id:
            coverage = patient.get('insurance_coverage_details', {})
            return {
                'coverage_limits': coverage.get('coverage_limits', {}),
                'out_of_pocket_max': coverage.get('out_of_pocket_max', 0.0)
            }
    return {
        'coverage_limits': {},
        'out_of_pocket_max': 0.0
    }

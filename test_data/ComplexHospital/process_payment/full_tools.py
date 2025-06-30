from models import AuthenticatedCustomerContext
from typing import Dict
import json
from agents import function_tool
import os
import random
import http.client

customer_data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'test_data', 'customer_data', 'hospital_utterance.json')
with open(customer_data_path, 'r') as f:
    customer_data = json.load(f)
    


#### CLIENT INFO TOOLS
async def get_billing_info(context: AuthenticatedCustomerContext) -> Dict:
    '''
    Retrieves billing information for a patient
    
    Args:
        context: The authenticated customer context containing the customer's ID.
    Returns:
        Dict: A dictionary containing outstanding balance, payment method, and payment plan status.
    '''
    for patient in customer_data:
        if patient['customer_id'] == context.customer_id:
            return {
                'outstanding_balance': patient['billing_info']['outstanding_balance'],
                'insurance_provider': patient['billing_info']['insurance_provider'],
                'payment_method': patient['billing_info']['payment_method'],
                'payment_plan_active': patient['billing_info']['payment_plan_active'],
                'hospital_id': patient['provider_details']['hospital_id']
            }
    return {}

async def check_account_status(context: AuthenticatedCustomerContext) -> Dict:
    """
    Checks the status of the customer's account.

    Args:
        context: The authenticated customer context containing the customer's ID.

    Returns:
        Dict: A dictionary with the account status.
    """
    for patient in customer_data:
        if patient['customer_id'] == context.customer_id:
            return {'status': patient['account_information']['status']}
    return {'status': 'unknown'}


async def evaluate_payment_urgency(context: AuthenticatedCustomerContext) -> Dict:
    """
    Evaluates how overdue a payment is and classifies the urgency level.

    Args:
        context: The authenticated customer context containing the customer's ID.

    Returns:
        Dict: A dictionary containing the urgency level ('low', 'medium', 'high') and days overdue.
    """
    for patient in customer_data:
        if patient['customer_id'] == context.customer_id:
            days_overdue = patient['billing_info']['days_overdue']
            if days_overdue < 3:
                urgency = "low"
            elif days_overdue < 30:
                urgency = "medium"
            else:
                urgency = "high"   
            return {
            "urgency": urgency,
            "days_overdue": days_overdue
        }
    return {
        "urgency": 'Not Found',
        "days_overdue": 'Not Found'
    }

async def calculate_late_fee_waiver_eligibility(context: AuthenticatedCustomerContext) -> Dict:
    """
    Determines whether the customer is eligible for a late fee waiver.

    Args:
        context: The authenticated customer context containing the customer's ID.

    Returns:
        Dict: A dictionary indicating eligibility and the waiver amount.
    """
    for patient in customer_data:
        if patient['customer_id'] == context.customer_id:
            eligible_for_waiver = patient['billing_info']['eligible_for_waiver']
            if eligible_for_waiver:
                waived_amount = patient['billing_info']['waiver_amount']
            else:
                waived_amount = 0.0
            
            return {'eligible for waiver': eligible_for_waiver, 'waiver_amount': waived_amount}
                    
    return {0.0}


#### MAIN TOOLS
@function_tool
async def get_insurance_payment_portion(customer_id: int, insurance_provider = str) -> Dict:
    """
    Determines whether part of the patient's balance can be covered by their insurance provider.

    Args:
        customer_id (int): The ID of the customer.
        insurance_provider (str): The customer's health insurance company. 

    Returns:
        Dict: Financial assistance status.
    """
    for patient in customer_data:
        if patient['customer_id'] == customer_id:
            financial_assistance_status = patient['billing_info']['financial_assistance_status']
            return {'financial_assistance_status': financial_assistance_status}
    return {'financial_assistance_status': 'Unknown'}



@function_tool
async def apply_fee_waiver(customer_id: int, waiver_amount: int) -> Dict:
    """
    Applies a fee waiver for a given customer.

    Args:
        customer_id (int): The ID of the customer.
        waiver_amount (int): The amount to be waived.

    Returns:
        Dict: Waiver result with status and amount.
    """
    for patient in customer_data:
        if patient['customer_id'] == customer_id:
            return {'waived': True, 'waiver_amount': waiver_amount}
    return {'waived': False, 'waiver_amount': 0.0}


@function_tool
async def currency_exchange(patient_responsibility_amount: float, from_currency: str, to_currency: str) -> Dict:
    """
    Converts an amount from one currency to another (mocked using RapidAPI).

    Args:
        patient_responsibility_amount (float): The amount to convert.
        from_currency (str): The source currency code.
        to_currency (str): The target currency code.

    Returns:
        Dict: Conversion result as a string (JSON).
    """
    conn = http.client.HTTPSConnection("currency-exchange.p.rapidapi.com")

    headers = {
        'x-rapidapi-key': "c2812472bamshabd9cfa9f3b6258p14b422jsn655e65eaefec",
        'x-rapidapi-host': "currency-exchange.p.rapidapi.com"
    }

    conn.request("GET", f"/exchange?from={from_currency}&to={to_currency}&q={patient_responsibility_amount}", headers=headers)

    res = conn.getresponse()
    data = res.read()

    data = data.decode("utf-8")

    converted_amount = round(float(data), 2)

    return converted_amount



@function_tool
async def calculate_patient_responsibility(customer_id: int, insurance_provider: str) -> Dict:
    """
    Calculates the patient's financial responsibility after applying assistance and waivers.

    Args:
        customer_id (int): The ID of the customer.
        insurance_provider (str): The customer's health insurance company. 


    Returns:
        Dict: Patient's final responsibility.
    """
    for patient in customer_data:
        if patient['customer_id'] == customer_id:
            outstanding_balance = patient['billing_info']['outstanding_balance']
            waiver_amount = patient['billing_info']['waiver_amount']
            final_amount = outstanding_balance - waiver_amount
            financial_assistance_status = patient['billing_info']['financial_assistance_status']
            if financial_assistance_status:
                return {
                    'patient_responsibility': round(final_amount * 0.4, 2)
                }
            else:
                return {
                    'patient_responsibility': round(final_amount, 2)
                }
    return {'patient_responsibility': 0.0}


@function_tool
async def get_hospital_contact_info(hospital_id: int) -> Dict:
    """
    Returns the contact information for a hospital.

    Args:
        customer_id (int): The ID of the hospital.

    Returns:
        Dict: Hospital hotline number.
    """
    return {'hotline': '1-800-555-BILL'}

@function_tool
async def initiate_3ds_auth(customer_id: int) -> Dict:
    """
    Initiates a 3DS (3-D Secure) authentication process.

    Args:
        customer_id (int): The ID of the customer.

    Returns:
        Dict: 3DS authentication success status.
    """
    success = random.random() > 0.2
    return {'3ds_success_status': success}

@function_tool
async def initiate_ach_transaction(customer_id: int, patient_responsibility_amount: float) -> Dict:
    """
    Initiates an ACH (Automated Clearing House) transaction.

    Args:
        customer_id (int): The ID of the customer.
        patient_responsibility_amount (float): The transaction amount.

    Returns:
        Dict: ACH transaction status.
    """
    # 10% chance of transient failure
    success = random.random() > 0.1
    return {'ach_success_status': 'initiated' if success else 'transient_error'}

@function_tool
async def get_wallet_link(customer_id: int) -> Dict:
    """
    Generates a wallet session link for a customer.

    Args:
        customer_id (int): The ID of the customer.

    Returns:
        Dict: A dictionary containing the wallet session URL and payment ID.
    """
    return {'url': f'https://wallet.payments.com/session/{customer_id}', 'payment_id': f'pay_{random.randint(1000,9999)}'}


@function_tool
async def check_wallet_payment_status(payment_id: str) -> Dict:
    """
    Checks the status of a digital wallet payment.

    Args:
        payment_id (str): The payment transaction ID.

    Returns:
        Dict: Payment success status.
    """
    # 100% chance of payment success
    success = True
    return {'digital_wallet_payment_success_status': success}
    
@function_tool
async def process_payment(customer_id: int, patient_responsibility_amount: float) -> Dict:
    """
    Processes a payment transaction for a customer.

    Args:
        customer_id (int): The ID of the customer.
        patient_responsibility_amount (float): The amount the customer is responsible for.

    Returns:
        Dict: Payment processing result.
    """
    # Simulate payment processing
    
    return {
        'paymentProcessed': True,
        'customer_id': customer_id
    }

@function_tool
async def issue_receipt(customer_id: int, patient_responsibility_amount: float) -> Dict:
    """
    Issues payment receipt.

    Args:
        customer_id (int): The ID of the customer.
        patient_responsibility_amount (float): The amount the customer is responsible for.

    Returns:
        Dict: Receipt sent status.
    """
    return {'receipt_sent': True}

@function_tool
async def setup_payment_plan(monthly_amount: float) -> Dict:
    """
    Sets up a monthly payment plan for the patient.

    Args:
        monthly_amount (float): The agreed monthly payment.

    Returns:
        Dict: Payment plan setup status and details.
    """
    # Simulate payment plan setup
    return {
        'paymentPlanSet': True,
        'monthlyAmount': monthly_amount
    }


@function_tool
async def get_provider_contact_info_api(customer_id: int) -> Dict:
    """
    Fetches provider contact information from the US Doctors API.

    Args:
        customer_id (int): The ID of the customer.

    Returns:
        Dict: Provider's phone number or error message.
    """
    provider_id = "1003975277" #default
    for patient in customer_data:
        if patient['customer_id'] == customer_id:
            provider_id = patient['provider_details']['provider_id']

    provider_id = int(provider_id)
    
    import http.client

    conn = http.client.HTTPSConnection("us-doctors-and-medical-professionals.p.rapidapi.com")

    headers = {
        'x-rapidapi-key': "c2812472bamshabd9cfa9f3b6258p14b422jsn655e65eaefec",
        'x-rapidapi-host': "us-doctors-and-medical-professionals.p.rapidapi.com"
    }

    conn.request("GET", f"/search_npi?npi={provider_id}", headers=headers)
    res = conn.getresponse()
    data = res.read()

    try:
        data = json.loads(data.decode("utf-8"))
    except json.JSONDecodeError:
        return {"phone": "Failed to decode API response"}

    if data.get('Code') == 200:
        phone_number = data.get('Data', {}).get('Provider_Business_Practice_Location_Address_Telephone_Number')
        if phone_number:
            return {"phone": phone_number}
        else:
            return {"phone": "Phone number not listed"}
    else:
        return {"phone": "No phone number found"}


        
@function_tool
async def run_fraud_check(customer_id: int, patient_responsibility_amount: float) -> Dict:
    """Flags suspicious payments (randomly).
    Args:
        customer_id (int): The unique identifier of the customer.
        patient_responsibility_amount (float): The transaction amount being checked.
    Returns:
        Dict: A dictionary with a single key:
            "flagged" (bool): Indicates whether the transaction was flagged as suspicious (True) or not (False)."""
    flagged = random.choices([True, False], weights=[0.1, 0.9])[0]
    return {"flagged": flagged}



########## EXTRA TOOL CALLS
@function_tool
async def get_billing_info_extra(customer_id: int) -> Dict:
    '''
    Retrieves billing information for a patient
    
    Args:
        customer_id (int): The unique identifier of the customer.
    Returns:
        Dict: A dictionary containing outstanding balance, payment method, and payment plan status.
    '''
    for patient in customer_data:
        if patient['customer_id'] == customer_id:
            return {
                'outstanding_balance': patient['billing_info']['outstanding_balance'],
                'paymentMethod': patient['billing_info']['payment_method'],
                'payment_plan_active': patient['billing_info']['payment_plan_active'],
                'hospital_id': patient['provider_details']['hospital_id']
            }
    return {}
    
@function_tool
async def check_account_status_extra(customer_id: int) -> Dict:
    """
    Checks the status of the customer's account.

    Args:
        customer_id (int): The unique identifier of the customer.

    Returns:
        Dict: A dictionary with the account status.
    """
    for patient in customer_data:
        if patient['customer_id'] == customer_id:
            return {'status': patient['account_information']['status']}
    return {'status': 'unknown'}


@function_tool
async def evaluate_payment_urgency_extra(customer_id: int) -> Dict:
    """
    Evaluates how overdue a payment is and classifies the urgency level.

    Args:
        customer_id (int): The unique identifier of the customer.

    Returns:
        Dict: A dictionary containing the urgency level ('low', 'medium', 'high') and days overdue.
    """
    for patient in customer_data:
        if patient['customer_id'] == customer_id:
            days_overdue = patient['billing_info']['days_overdue']
            if days_overdue < 3:
                urgency = "low"
            elif days_overdue < 30:
                urgency = "medium"
            else:
                urgency = "high"   
            return {
            "urgency": urgency,
            "days_overdue": days_overdue
        }
    return {
        "urgency": 'Not Found',
        "days_overdue": 'Not Found'
    }

@function_tool
async def calculate_late_fee_waiver_eligibility_extra(customer_id: int) -> Dict:
    """
    Determines whether the customer is eligible for a late fee waiver.

    Args:
        customer_id (int): The unique identifier of the customer.

    Returns:
        Dict: A dictionary indicating eligibility and the waiver amount.
    """
    for patient in customer_data:
        if patient['customer_id'] == customer_id:
            eligible_for_waiver = patient['billing_info']['eligible_for_waiver']
            if eligible_for_waiver:
                waived_amount = patient['billing_info']['waiver_amount']
            else:
                waived_amount = 0.0
            
            return {'eligible for waiver': eligible_for_waiver, 'waiver_amount': waived_amount}
                    
    return {'eligible': False, 'waiver_amount': 0.0}
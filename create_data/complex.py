import json

routine_data = {
    "book_appointment": json.load(open("../test_data/ComplexHospital/book_appointment/full_workflow.json")),
    "process_payment": json.load(open("../test_data/ComplexHospital/process_payment/full_workflow.json"))
}

required_fields = ['agent_sequence',
                    'customer_id',
                   
                    "account_information['status']", 
                    "provider_details['hospital_id']",
                    "provider_details['provider_id']",

                    "billing_info['outstanding_balance']",
                   "billing_info['insurance_provider']",
                    "billing_info['waiver_amount']",
                    "billing_info['payment_method']",
                    "billing_info['payment_id']",
                   "billing_info['payment_plan_active']",
                    "billing_info['financial_assistance_status']",
                   "billing_info['eligible_for_waiver']",
                   "billing_info['days_overdue']",

                    "user_provided_info['wants_to_proceed_post_final_amount']",
                    "user_provided_info['payment_currency_other_than_usd_requested']",
                    "user_provided_info['payment_currency_preferred']",
                    "user_provided_info['payment_plan_monthly_amount']",
                   "user_provided_info['wants_fee_waiver']",
                   "user_provided_info['payment_plan_setup_requested']",

                    "user_provided_info['authenticator_code']",
                   "user_provided_info['mobile_phone_number']",
                   "contact_info['mobile_phone_number']",
                   "authenticator_api['authenticator_code']",



                   "patient_info['zip_code']",
                   "patient_info['language_preference']",
                   "patient_info['preferred_hospital']",
                   "patient_info['age']",
                   
                   "emergency_contact['name']",
                   "emergency_contact['email']",
                   
                   "referral_info['has_referral']",

                   "medical_info['critical_conditions']",
                   "medical_info['last_appointment_type']",

                    "user_provided_info['preferred_datetime']",
                   "user_provided_info['route_to_specialist']",
                    "user_provided_info['symptoms']",


                   "communication_preferences['reminder_preference']",
                   
                   "insurance_coverage_details['coverage_limits']",
                    "insurance_coverage_details['out_of_pocket_max']",             
]

zip_code = {
    "10001": 0.25,
    "94103": 0.2,
    "30301": 0.15,
    "60601": 0.25,
    "73301": 0.15
}

preferred_hospital = {
    "UNC Health": 0.3,
    "Cleveland Clinic": 0.25,
    "Mayo Clinic": 0.2,
    "Mass General": 0.15,
    "UCLA Health": 0.1
}

name = {
    "Alice Smith": 0.3,
    "John Doe": 0.25,
    "Maria Garcia": 0.2,
    "Wei Chen": 0.15,
    "Amit Patel": 0.1
}

language_preference = {
    "EN": 0.7,
    "ES": 0.2,
    "ZH": 0.05,
    "AR": 0.05
}

email = {
    "user1283@domain.com": 0.3,
    "mailbox462@domain.com": 0.25,
    "contact982@domain.com": 0.2,
    "info2441@domain.com": 0.15,
    "account743@domain.com": 0.1
}

critical_conditions = {
    None: 0.92,
    "Heart Failure": 0.03,
    "Respiratory Distress": 0.03,
    "Severe Infection": 0.02
}


symptoms = {
    "chest pain": 0.3,
    "rash": 0.2,
    "dizziness": 0.25,
    "fatigue": 0.15,
    "nausea": 0.1
}

providers = {
    "1003975277": 0.1,
    "1013996552": 0.15,
    "1023041837": 0.05,
    "1043455892": 0.2,
    "1093947798": 0.3,
    "1104946060": 0.2
}

insurance_providers = {
    "BluePeak": 0.25,
    "Aetralis": 0.25,
    "Humena": 0.25,
    "Cignexa": 0.25
}

currency = {
    "USD": 0.8
    "THB": 0.05,
    "CNY": 0.05,
    "AUD": 0.05,
    "IDR": 0.05
}


template = {
'agent_sequence': {'process_payment': 50},
'customer_id': {'random_int(10000000, 99999999)': 1.0}, 
"contact_info['mobile_phone_number']": {'random_int(1000000000, 9999999999)': 1.0},
"authenticator_api['authenticator_code']": {'random_int(100000, 999999)': 1.0},
    
"account_information['status']": {"suspended":0.2, "delinquent":0.1, "active":0.7}, 
    
"provider_details['hospital_id']": {'random_int(120000, 690000)': 1.0},
"provider_details['provider_id']":providers ,

"billing_info['outstanding_balance']": {'random_int(20, 2500)': 1.0},
"billing_info['waiver_amount']": {'random_int(0, 15)': 1.0},
"billing_info['payment_method']": {"Credit Card": 0.4, "Bank Transfer": 0.3, "Digital Wallet": 0.3},
"billing_info['payment_id']":{'random_int(10000, 99999)': 1.0},
"billing_info['payment_plan_active']":{'true': 0.3, 'false': 0.7},
"billing_info['financial_assistance_status']":{'true': 0.7, 'false': 0.3},
"billing_info['eligible_for_waiver']": {'true': 0.5, 'false': 0.5},
"billing_info['days_overdue']": {'random_int(0, 45)': 1.0},
"billing_info['insurance_provider']": insurance_providers,
    
"user_provided_info['payment_currency_other_than_usd_requested']": {'true': 0.2, 'false': 0.8},
"user_provided_info['payment_currency_preferred']": currency,
    
"user_provided_info['wants_to_proceed_post_final_amount']": {'true': 1.0},
"user_provided_info['wants_fee_waiver']":{'true': 1.0},
    
"user_provided_info['payment_plan_setup_requested']":{'true': 0.5, 'false': 0.5},
"user_provided_info['payment_plan_monthly_amount']":{'random_int(10, 200)': 1.0},



"patient_info['zip_code']": zip_code,
"patient_info['language_preference']":language_preference,
"patient_info['preferred_hospital']": preferred_hospital,
"patient_info['age']":{'random_int(12, 100)': 1.0},

"emergency_contact['name']": name,
"emergency_contact['email']":email,

"referral_info['has_referral']":{'true': 0.8, 'false': 0.1},

"medical_info['critical_conditions']":critical_conditions,
"medical_info['last_appointment_type']": symptoms,

"user_provided_info['preferred_datetime']": {"random_date('2025-08-01', '2025-08-15')": 1.0},
"user_provided_info['route_to_specialist']": {'true': 0.2, 'false': 0.8},
"user_provided_info['symptoms']": {
                    'same_as': "medical_info['last_appointment_type']",  
                    'probability': 1
                        },


"communication_preferences['reminder_preference']":{'true': 0.5, 'false': 0.5},

"insurance_coverage_details['coverage_limits']":{'random_int(200, 500)': 1.0},
"insurance_coverage_details['out_of_pocket_max']" :{'random_int(500, 4000)': 1.0},

"user_provided_info['mobile_phone_number']": {
                    'same_as': "contact_info['mobile_phone_number']",  
                    'probability': 1
                        },
"user_provided_info['authenticator_code']": {
                    'same_as': "authenticator_api['authenticator_code']",  
                    'probability': 1
                        }
}
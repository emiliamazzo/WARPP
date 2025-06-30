import json

routine_data = {
    "update_address": json.load(open("../test_data/SimpleBanking/update_address/full_workflow.json")),
    "withdraw_retirement_funds": json.load(open("../test_data/SimpleBanking/withdraw_retirement_funds/full_workflow.json"))
}

required_fields = ['agent_sequence',
                    'customer_id',
                    'client_level',
                    'account_type',
                    'account_balance',
                    "contact_info['mobile_phone_number']",
                    "authenticator_api['authenticator_code']",
                    "user_provided_info['address']['city']",
                    "user_provided_info['address']['state']",
                    "user_provided_info['address']['street']",
                    "user_provided_info['address']['country']",
                    "user_provided_info['address']['zip_code']",
                    "user_provided_info['withdrawal']['withdrawal_amount']",
                    "user_provided_info['mobile_phone_number']",
                    "user_provided_info['authenticator_code']"              
                  ]
                

street = {
        "123 Main St": 0.2,
        "742 Evergreen Terrace": 0.2,      
        "1600 Pennsylvania Ave": 0.15,    
        "1313 Mockingbird Lane": 0.15,     
        "221B Baker St": 0.15,             
        "42 Wallaby Way": 0.15           
    }

city = {
    "Springfield": 0.2,  
    "Riverside": 0.2,     
    "Greenville": 0.15,   
    "Fairview": 0.15,    
    "Clinton": 0.15,     
    "Madison": 0.1,      
    "Quahog": 0.05        
}


state = {
        "MA": 0.2,  
        "NC": 0.2,  
        "IL": 0.2,  
        "RI": 0.15, 
        "NY": 0.15, 
        "CA": 0.1  
    }

zip_codes = {
        "02118": 0.2,  
        "28202": 0.2,  
        "27601": 0.2,  
        "62704": 0.15, 
        "02860": 0.15, 
        "90210": 0.1  
    }


template = {
    'customer_id': {'random_int(10000000, 99999999)': 1.0},
    'agent_sequence': {'update_address': 50, 'withdraw_retirement_funds': 50},
    'account_type': {"401K": 0.2, "TRADITIONAL_IRA": 0.4, "ROTH_IRA": 0.4},
    'account_balance': {'random_int(1000, 99999)': 1.0},
    "contact_info['mobile_phone_number']": {'random_int(1000000000, 9999999999)': 1.0},
    "authenticator_api['authenticator_code']": {'random_int(100000, 999999)': 1.0},
    'client_level': {'PREMIUM':0.3, 'STANDARD':0.7},
    "user_provided_info['address']['street']": street,
    "user_provided_info['address']['city']": city,
    "user_provided_info['address']['state']": state,
    "user_provided_info['address']['country']": {"USA": 1.0},
    "user_provided_info['address']['zip_code']": zip_codes,
    "user_provided_info['withdrawal']['withdrawal_amount']": {'random_int(100, 999)': 1.0},
    "user_provided_info['mobile_phone_number']": {
                    'same_as': "contact_info['mobile_phone_number']",  
                    'probability': 1
                        },
    "user_provided_info['authenticator_code']": {
                    'same_as': "authenticator_api['authenticator_code']",  
                    'probability': 1
                        }

, 
}
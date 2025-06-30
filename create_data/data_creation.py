import sys
import os
import json
import importlib
import argparse
from traxgen import generate_user_profiles
import json

sys.path.append(os.path.abspath('..')) 

def main(complexity):
    if complexity == 'simple':
        output_folder_domain = 'banking'
    elif complexity == 'intermediate':
        output_folder_domain = 'flights'
    elif complexity == 'complex':
        output_folder_domain = 'hospital'
        
    routine_module = importlib.import_module(complexity)

    output_path = f"../test_data/customer_data/{output_folder_domain}.json"

    required_fields = routine_module.required_fields
    template = routine_module.template

    profile = generate_user_profiles(
        fields = required_fields,
        field_distributions = template,
        write_to_file=True,
        output_path=output_path
    )

    #### small waiver amount adjustment needed for hospital.
    if output_folder_domain == 'hospital':
        with open(output_path, 'r') as f:
            customer_data = json.load(f)
            
        for patient in customer_data:
            billing = patient.get('billing_info', {})
            if billing.get('eligible_for_waiver') is False:
                billing['waiver_amount'] = 0

            upi = patient.setdefault('user_provided_info', {})
            if not upi.get('payment_currency_other_than_usd_requested', False):
                upi['payment_currency_preferred'] = 'USD'
    
            if not upi.get('payment_plan_setup_requested', False):
                upi['payment_plan_monthly_amount'] = 0
            
        with open(output_path, 'w') as f:
            json.dump(customer_data, f, indent=2)

        

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--complexity", required=True, help="Routine complexity (e.g., simple, moderate, complex)")
    args = parser.parse_args()
    main(args.complexity)
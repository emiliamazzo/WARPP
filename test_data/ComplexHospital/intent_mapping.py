INTENT_MAPPING = {
    "book_appointment_intent": {
        "intent": "book_appointment",
        "client_info_tools": [
            'get_patient_profile_extra',
            'get_insurance_coverage_details', 
            'get_medical_history_summary',
            'check_if_customer_has_referral',
            'get_emergency_contact'
        ],
        "client_info_tools_extra": [
            'get_patient_profile_extra',
            'get_insurance_coverage_details_extra',
            'get_medical_history_summary_extra', 
            'check_if_customer_has_referral_extra',
            'get_emergency_contact_extra'
        ],
        "execution_tools": [
            'set_up_reminder',
            'find_available_appointments', 
            'book_appointment',
            'check_appointment_conflict_live_api',
            'get_hospital_bed_availability_api',
            'get_provider_contact_info_api',
            'suggest_nearest_hospital',
            'get_estimated_wait_time',
            'get_provider_rating',
            'check_insurance_plan_validity',
            'suggest_appointment_type',
            'get_patient_demographics',
            'get_patient_demographics_extra',
            'assign_language_support',
            'set_guardian_contact',
            'suggest_accessible_hospitals',
            'collect_emergency_contact',
            'route_to_specialist',
            'route_to_financial_support'
        ]
    },
    "process_payment_intent": {
        "intent": "process_payment",
        "client_info_tools": [
            'get_billing_info',
            'get_insurance_payment_portion',
            'check_account_status',
            'evaluate_payment_urgency',
            'calculate_late_fee_waiver_eligibility'
        ],
        "client_info_tools_extra": [
            'get_billing_info_extra',
            'check_account_status_extra',
            'evaluate_payment_urgency_extra',
            'calculate_late_fee_waiver_eligibility_extra'
        ],
        "execution_tools": [
            'calculate_patient_responsibility',
            'apply_fee_waiver',
            'process_payment',
            'setup_payment_plan',
            'currency_exchange',
            'get_hospital_contact_info',
            'run_fraud_check',
            'initiate_3ds_auth',
            'initiate_ach_transaction',
            'get_wallet_link',
            'check_wallet_payment_status',
            'get_provider_contact_info_api'
        ]
    },
}

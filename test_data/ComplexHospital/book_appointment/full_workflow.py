book_appointment_workflow = """
1. Get Patient Profile
   a. Call `get_patient_profile_extra(customer_id)` to retrieve:
      - patient_info, insurance_info, medical_info, communication_preferences

2. Medical History Check
   a. Call `get_medical_history_summary_extra(customer_id)`
      - If medical_history_summary['critical_conditions'] is not empty:
         - Inform: "You have a critical condition: {condition}."
         - Ask: "Do you prefer routing to a specialist?"
            - If YES → call `route_to_specialist(customer_id)` → Step 16
            - If NO → continue

3. Emergency Contact Verification
   a. Call `get_emergency_contact_extra(customer_id)`
      - If missing/invalid → call `collect_emergency_contact(customer_id)` → Confirm

4. Patient Demographics-Based Fork
   a. Call `get_patient_demographics_extra(customer_id)`
      - If age < 18:
              - Inform the user that, since they are trying to book an appointment for a minor, you need to set up the guardian contact. 
            - Call `set_guardian_contact(customer_id)`
      - If language_preference != 'EN':
         - Call `assign_language_support(customer_id, language_preference)`

5. Billing Eligibility Check
    a. Inform the client you will check their billing eligibility.
   b. If billing_info['outstanding_balance'] > 1000 AND billing_info['payment_plan_active'] == False:
      - Inform: "Outstanding balance detected."
      - Call `route_to_financial_support(customer_id)` → Step 16

6. Referral Requirement Check
    - Inform the client you will check if they need a referral for their appointment.
  - Call `check_if_customer_has_referral_extra(customer_id)`
  - If no referral:
        -Step 16

7. Insurance Validity Check
   a. Inform the client you are about to check their insurance information.
   b. Call `check_insurance_plan_validity(customer_id)`

8. Insurance Coverage Check
   a. Call `get_insurance_coverage_details_extra(customer_id)`
      - If estimated_cost > coverage_limits[amount]:
         - Inform the customer that they may have out-of-pocket costs.

9. Hospital Evaluation
  - Call `get_hospital_bed_availability_api(hospital_id)`
     - If beds_available == 0:
        - Call `suggest_nearest_hospital(zip_code)`


10. Appointment Availability
    a. Inform the client you are about to look for appointments available.
   a. Call `find_available_appointments(customer_id)`
      - If no match:
         - Ask: "Join waitlist or retry?"
            - If NO → Call `complete_case(customer_id)` and end
            - If YES → continue

11. Appointment Type Determination
   a. If medical_info['last_appointment_type'] exists:
      - Confirm the type of appointment with the user before proceeding to step 12. 
   b. Else:
      - Ask: "What symptoms are you experiencing?"
      - Call `suggest_appointment_type(symptom_description)`
      - If suggested type is specialist-only:
            - If no referral → Mention to the user that they will have to find a referral before the appointment date.

12. Check Date/Time & Conflicts
   a. Ask for preferred date
   b. Call `check_appointment_conflict_live_api(customer_id, date)`
      - If conflict:
         - Ask for new time → repeat until clear
      - If urgent flag set from Step 2:
         - Prioritize earliest available slot

13. Book Appointment
   a. Call `book_appointment(customer_id)`

14. Get the provider contact information.
    a. Call `get_provider_contact_info_api(provider_id)` to get the phone number of the doctor and share with the client.

15. Set Reminder
   a. If communication_preferences['reminder_preference'] != none:
      - Call `set_up_reminder(customer_id)`

16. Complete Case
   a. Call `complete_case(customer_id)` and summarize the details of the conversation.
"""


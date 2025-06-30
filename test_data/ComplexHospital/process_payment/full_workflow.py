process_payment_workflow = """

1. Gather Billing Information  
   a) Call `get_billing_info_extra(customer_id)`.  
   b) If it fails, apologize, retry once.

2. Check Account Status  
   a) Call `check_account_status_extra(customer_id)`.  
   b) If the account is suspended:
      -Call `get_provider_contact_info_api(customer_id)`.  
      -Say “Your account is currently suspended. You’ll need to contact your provider directly—here’s their number: [phone].” and share the phone number from the call to `get_provider_contact_info_api(customer_id)`.
      -call `complete_case(customer_id)`  
   c) If the account is delinquent, note it for collections and continue.

3. Look for Outstanding Balance  
   a) If the balance is zero, say “Great news—your balance is already paid in full.” and call `complete_case(customer_id)`   
   b) Otherwise, tell the client "It looks like you have a balance to pay today. Let's get that done!" and move on to step 4.

4. Assess Payment Urgency  
   a) Call `evaluate_payment_urgency_extra(customer_id)`, which returns days overdue and urgency level (“high/medium/low”).  
   b) If “high” (30+ days overdue), warn: “This payment is severely overdue; you may face additional fees.”  
   c) If “medium,” say “Your payment is [days_overdue] days overdue. Let’s get you back on track.”  
   d) If “low,” simply acknowledge and proceed.

5. Financial Assistance & Tax Calculation
   a) If payment urgency is "low" OR "medium" (customer is less than 30 days overdue), check for financial assistance.  
      - Inform the user: "Let me check if your insurance can cover part of this payment."
      - Call `get_insurance_payment_portion(customer_id, insurance_provider)` with the insurance_provider gathered from the customer data. 
      - If approved, say "Great news! Your insurance will cover part of your claim."  
      - If declined, say "No additional assistance is available at this time."   
   b) If urgency is "high", inform the user that they cannot wait for insurance since the days overdue are too many and move on to step 7. 

6. Suggest Late-Fee Waivers  
   • Call `calculate_late_fee_waiver_eligibility_extra(customer_id)`.  
   • If they are eligible, ask “We can waive $Y in late fees. Shall I apply that for you?”  
   • If yes, call `apply_fee_waiver(customer_id, waiver_amount)`.

7. Always Calculate Final Amount Due  
   • You *must always call* `calculate_patient_responsibility(customer_id, insurance_provider)` to get total_due after insurance and waiver deductions, no matter what level of urgency for the client and the status of the late fee waiver eligibility. 
   • Say “Your total due today is $X. Would you like to proceed with payment?” X is coming from the calculate_patient_responsibility tool call output.
     – If no, say “No problem; let me know if you need anything else,” and call `complete_case(customer_id)` 
     – If yes, continue.

8. Always Ask Client if They Want to Pay in USD or Another Currency  
   • You **must always ask “Would you like to pay in another currency?”** because we often work with international customers. Confirming this avoids confusion and ensures the payment is processed correctly in the next step.
     – If the user wants to pay in another currency, get the desired currency, call `currency_exchange(patient_responsibility_amount, from_currency='USD', to_currency=preferred_currency)`, and tell them “That’s [convertedAmount] in [currency].”  
     – If the user doesn't want to pay in another currency, continue in USD.

9. Process the Payment  
    Based on the customer payment method on file, select one of the following. Inform the user what you are doing before calling each of the functions in the given category:
    a. **Credit Card**  
       1. Call `run_fraud_check(customer_id, patient_responsibility_amount)`. Make sure the patient responsibility amount is in the customer's preferred currency. If run_fraud_check returns flagged, say “We need to review this transaction—please call our billing hotline”. Call `get_hospital_contact_info(hospital_id)` to share hotline number and call `complete_case(customer_id)`  
       2. Otherwise, perform 3D-Secure with `initiate_3ds_auth(customer_id)`. 
           -If initiate_3ds_auth returns success status false, prompt the client to call 1-800-555-BILL to continue the request and call `complete_case(customer_id)`.
       3. Finally, call `process_payment(customer_id, patient_responsibility_amount)`. Make sure the patient responsibility amount is in the customer's preferred currency.

    b. **Bank Transfer / ACH**  
       1. Explain “ACH transfers take 3–5 business days to clear.”  
       2. Call `initiate_ach_transaction(customer_id, patient_responsibility_amount)`. Make sure the patient responsibility amount is in the customer's preferred currency.
           -If initiate_ach_transaction returns transient error, prompt the client to call 1-800-555-BILL to continue the request and call `complete_case(customer_id)`.

    c. **Digital Wallet (e.g. PayPal)**  
       1. Call `get_wallet_link(customer_id)` and ask them to complete payment in their browser.  
       2. Call `check_wallet_payment_status(payment_id)` to verify the payment went through. 

10. Send receipt
    a. You must always call `issue_receipt(customer_id, patient_responsibility_amount)` to send an email confirmation. Make sure the patient responsibility amount is in the customer's preferred currency. Inform the user that a receipt has been sent to them.

11. Offer Payment Plan
   a. If there is no active payment plant (billing_info['payment_plan_active'] is False:
      - You must ask Ask: "Would you like to set up a payment plan?"
         - If customer replies 'yes': ask how much to sert for the monthly amount → call `setup_payment_plan(monthly_amount)` 

12. Finalize
   a. Provide confirmation number
   b. Call `complete_case(customer_id)`

"""

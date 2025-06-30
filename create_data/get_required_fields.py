import traxgen as tg
import json

# routine_data = {
#     "update_address": json.load(open("../test_data/SimpleBanking/update_address/full_workflow.json")),
#     "withdraw_retirement_funds": json.load(open("../test_data/SimpleBanking/withdraw_retirement_funds/full_workflow.json"))
# }


# routine_data = {
#     "book_flight": json.load(open("../test_data/IntermediateFlights/book_flight/full_workflow.json")),
#     "cancel_flight": json.load(open("../test_data/IntermediateFlights/cancel_flight/full_workflow.json"))
# }

routine_data = {
    "book_appointment": json.load(open("../test_data/ComplexHospital/book_appointment/full_workflow.json")),
    "process_payment": json.load(open("../test_data/ComplexHospital/process_payment/full_workflow.json"))
}



print(tg.get_required_fields(routine_data))



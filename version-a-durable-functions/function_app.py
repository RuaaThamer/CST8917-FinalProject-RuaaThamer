import logging
from datetime import timedelta
import azure.functions as func
import azure.durable_functions as df

my_app = df.DFApp(http_auth_level=func.AuthLevel.ANONYMOUS)

VALID_CATEGORIES = {"travel", "meals", "supplies", "equipment", "software", "other"}
REQUIRED_FIELDS = {"employee_name", "employee_email", "amount", "category", "description", "manager_email"}

# ---------------------------------------------------------
# 1. HTTP STARTER (Client)
# ---------------------------------------------------------
@my_app.route(route="orchestrators/expense_orchestrator")
@my_app.durable_client_input(client_name="client")
async def http_start(req: func.HttpRequest, client) -> func.HttpResponse:
    try:
        expense_data = req.get_json()
    except ValueError:
        return func.HttpResponse("Invalid JSON payload", status_code=400)

    instance_id = await client.start_new("expense_orchestrator", client_input=expense_data)
    logging.info(f"Started orchestration with ID = '{instance_id}'.")
    return client.create_check_status_response(req, instance_id)

# ---------------------------------------------------------
# 2. ORCHESTRATOR
# ---------------------------------------------------------
@my_app.orchestration_trigger(context_name="context")
def expense_orchestrator(context: df.DurableOrchestrationContext):
    expense = context.get_input()

    # Activity 1: Validate
    validation = yield context.call_activity("validate_activity", expense)
    if not validation["is_valid"]:
        yield context.call_activity("notify_activity", {"email": expense.get("employee_email"), "status": "REJECTED", "reason": validation["error"]})
        return {"status": "FAILED_VALIDATION", "error": validation["error"]}

    amount = float(expense.get("amount", 0))

    # Business Rule: Auto-Approve under $100
    if amount < 100:
        outcome, reason = "APPROVED", "Auto-approved (Amount < $100)"
    else:
        # Human Interaction Pattern: Wait for Manager or Timeout (2 minutes)
        timeout_time = context.current_utc_datetime + timedelta(minutes=2)
        durable_timer = context.create_timer(timeout_time)
        manager_event = context.wait_for_external_event("ManagerDecision")

        # Race condition
        winner = yield context.task_any([manager_event, durable_timer])

        if winner == manager_event:
            durable_timer.cancel()
            decision = manager_event.result.get("decision", "").upper()
            if decision == "APPROVE":
                outcome, reason = "APPROVED", "Manager Approved"
            else:
                outcome, reason = "REJECTED", "Manager Rejected"
        else:
            outcome, reason = "ESCALATED", "Manager timeout (auto-escalated)"

    # Activity 2 & 3: Process and Notify
    yield context.call_activity("process_activity", {"expense": expense, "outcome": outcome, "reason": reason})
    yield context.call_activity("notify_activity", {"email": expense.get("employee_email"), "status": outcome, "reason": reason})

    return {"status": outcome, "reason": reason}

# ---------------------------------------------------------
# 3. MANAGER APPROVAL WEBHOOK (Client)
# ---------------------------------------------------------
@my_app.route(route="approve_expense/{instance_id}")
@my_app.durable_client_input(client_name="client")
async def manager_webhook(req: func.HttpRequest, client) -> func.HttpResponse:
    instance_id = req.route_params.get("instance_id")
    body = req.get_json()
    decision = body.get("decision")
    
    await client.raise_event(instance_id, "ManagerDecision", {"decision": decision})
    return func.HttpResponse(f"Decision '{decision}' sent to instance {instance_id}.", status_code=200)

# ---------------------------------------------------------
# 4. ACTIVITIES
# ---------------------------------------------------------
@my_app.activity_trigger(input_name="expense")
def validate_activity(expense: dict) -> dict:
    missing = [f for f in REQUIRED_FIELDS if not expense.get(f)]
    if missing:
        return {"is_valid": False, "error": f"Missing: {', '.join(missing)}"}
    
    cat = str(expense.get("category", "")).lower()
    if cat not in VALID_CATEGORIES:
        return {"is_valid": False, "error": f"Invalid category."}
    return {"is_valid": True, "error": ""}

@my_app.activity_trigger(input_name="details")
def process_activity(details: dict) -> str:
    logging.info(f"Processing outcome: {details['outcome']} for {details['expense']['employee_name']}")
    return "Processed"

@my_app.activity_trigger(input_name="notification")
def notify_activity(notification: dict) -> str:
    logging.info(f"EMAIL SENT TO {notification['email']}: {notification['status']} - {notification['reason']}")
    return "Notified"
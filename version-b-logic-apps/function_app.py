import azure.functions as func
import json

app = func.FunctionApp()

VALID_CATEGORIES = {"travel", "meals", "supplies", "equipment", "software", "other"}
REQUIRED_FIELDS = {"employee_name", "employee_email", "amount", "category", "description", "manager_email"}

@app.route(route="validate_expense", auth_level=func.AuthLevel.ANONYMOUS)
def validate_expense(req: func.HttpRequest) -> func.HttpResponse:
    try:
        expense = req.get_json()
    except ValueError:
        return func.HttpResponse(json.dumps({"is_valid": False, "error": "Invalid JSON payload"}), status_code=400, mimetype="application/json")
    
    missing = [f for f in REQUIRED_FIELDS if not expense.get(f)]
    if missing:
        return func.HttpResponse(json.dumps({"is_valid": False, "error": f"Missing: {', '.join(missing)}"}), status_code=400, mimetype="application/json")
    
    cat = str(expense.get("category", "")).lower()
    if cat not in VALID_CATEGORIES:
        return func.HttpResponse(json.dumps({"is_valid": False, "error": "Invalid category."}), status_code=400, mimetype="application/json")
        
    return func.HttpResponse(json.dumps({"is_valid": True, "error": ""}), status_code=200, mimetype="application/json")
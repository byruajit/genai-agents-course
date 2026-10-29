"""Session 20 data - function calling: BankAssist from Session 19, now with three tools.

  TOOLS            three tool schemas in the OpenAI "tools" format (JSON Schema for the arguments). The
                   description of each tool is a prompt: it is the only thing the model reads to decide WHEN
                   to call it.
  RATE_CARD        today's rates - the "live data" get_rate looks up, instead of numbers baked into a prompt.
  FOIR_LIMIT       Northwind's simplified lending rule: all EMIs together must stay at or below 50% of monthly
                   income (FOIR = fixed obligations to income ratio). Real banks use 40-60% depending on income
                   band and product; one number keeps the lab readable.
  TOOLS_GUIDANCE   Fix A: one paragraph added to the system prompt saying when NOT to call a tool.
  ROUTER_PROMPT    Fix C: a one-word classifier (Session 16's idea) that decides TOOL or NO_TOOL first.
  GOLDEN           10 questions with known right answers: 6 need a tool (one needs two steps, one is a
                   "not eligible" case), 4 need no tool at all. Scored three ways in tool_utils.score_question.
  WAYS             the four ways the golden set is run: no fix, Fix A, Fix B, Fix C.
"""
from __future__ import annotations

from chat_tasks import BANKASSIST_SYSTEM  # noqa: F401 - re-exported: today's assistant is Session 19's

# ---------------------------------------------------------------- live data the tools read
RATE_CARD = {
    ("home_loan", "floating"): 8.5,
    ("home_loan", "fixed"): 9.0,
    ("personal_loan", "fixed"): 10.5,
}
FOIR_LIMIT = 0.50

# ---------------------------------------------------------------- the three tool schemas
TOOLS = [
    {"type": "function", "function": {
        "name": "calculate_emi",
        "description": ("Exact monthly EMI (instalment) for a loan. Use ONLY when the customer asks for an EMI or "
                        "monthly instalment amount and has given the loan amount, rate and tenure."),
        "parameters": {"type": "object", "properties": {
            "principal": {"type": "number", "description": "Loan amount in rupees, e.g. 25 lakh = 2500000"},
            "annual_rate": {"type": "number", "description": "Interest rate in percent per year, e.g. 8.5"},
            "tenure_months": {"type": "integer", "description": "Total months, e.g. 20 years = 240"}},
            "required": ["principal", "annual_rate", "tenure_months"]}}},
    {"type": "function", "function": {
        "name": "get_rate",
        "description": ("Today's interest rate for a loan product from Northwind's rate card. Use when the customer "
                        "asks for a current rate, or needs one to work out an EMI."),
        "parameters": {"type": "object", "properties": {
            "product": {"type": "string", "enum": ["home_loan", "personal_loan"]},
            "rate_type": {"type": "string", "enum": ["floating", "fixed"],
                          "description": "Personal loans are fixed-rate only."}},
            "required": ["product", "rate_type"]}}},
    {"type": "function", "function": {
        "name": "check_eligibility",
        "description": ("Checks whether a new EMI is affordable under Northwind's rule: all EMIs together must be at "
                        "most 50% of monthly income. Use when the customer asks if they are eligible or can afford it."),
        "parameters": {"type": "object", "properties": {
            "monthly_income": {"type": "number", "description": "Take-home income per month in rupees"},
            "existing_emi": {"type": "number", "description": "EMIs already being paid per month, 0 if none"},
            "proposed_emi": {"type": "number", "description": "The new EMI per month in rupees"}},
            "required": ["monthly_income", "existing_emi", "proposed_emi"]}}},
]

# ---------------------------------------------------------------- Fix A: tell it when NOT to call a tool
TOOLS_GUIDANCE = """
# Tools
You have three tools: calculate_emi, get_rate, check_eligibility.
Call a tool ONLY when the customer asks for an EMI amount, today's rate, or whether they are eligible.
For anything else - branch timings, documents, greetings, policy questions answered by the facts above -
answer directly, with NO tool call.
Never invent an argument the customer did not give you; ask for it instead.
"""

# ---------------------------------------------------------------- Fix C: route first (Session 16's classifier, new job)
ROUTER_PROMPT = """You are a router for a bank's customer assistant. Read the customer's message and reply with
exactly one word:
TOOL     - if answering needs an exact EMI calculation, today's interest rate, or an eligibility check.
NO_TOOL  - for everything else: branch timings, documents, fees and policies, greetings, thanks.
Reply with TOOL or NO_TOOL and nothing else."""

# ---------------------------------------------------------------- the golden set
# expect_tools: the set of tools a correct run calls (order ignored). Empty = answer without any tool.
# expect_args:  for the main tool, the argument values a correct call uses (numbers compared within 0.5%).
# answer_any:   the final text must contain at least one of these (lowercase, commas and spaces removed).
# answer_not:   ...and none of these.
GOLDEN = [
    {"id": "g1", "question": "What is the EMI on a 25 lakh home loan at 8.5% for 20 years?",
     "expect_tools": ["calculate_emi"],
     "expect_args": {"calculate_emi": {"principal": 2500000, "annual_rate": 8.5, "tenure_months": 240}},
     "answer_any": ["21696", "21695"], "answer_not": []},
    {"id": "g2", "question": "I want a personal loan of 5 lakh at 10.5% for 3 years. What will my monthly EMI be?",
     "expect_tools": ["calculate_emi"],
     "expect_args": {"calculate_emi": {"principal": 500000, "annual_rate": 10.5, "tenure_months": 36}},
     "answer_any": ["16251"], "answer_not": []},
    {"id": "g3", "question": "What is your home loan floating rate today?",
     "expect_tools": ["get_rate"],
     "expect_args": {"get_rate": {"product": "home_loan", "rate_type": "floating"}},
     "answer_any": ["8.5"], "answer_not": []},
    {"id": "g4", "question": "What would my EMI be on a 30 lakh home loan at your floating rate, over 15 years?",
     "expect_tools": ["get_rate", "calculate_emi"],
     "expect_args": {"calculate_emi": {"principal": 3000000, "annual_rate": 8.5, "tenure_months": 180}},
     "answer_any": ["29542"], "answer_not": []},
    {"id": "g5", "question": ("I earn 80,000 a month and already pay 15,000 in EMIs. Would a new EMI of 21,696 "
                              "be within your limit?"),
     "expect_tools": ["check_eligibility"],
     "expect_args": {"check_eligibility": {"monthly_income": 80000, "existing_emi": 15000, "proposed_emi": 21696}},
     "answer_any": ["eligible", "within", "yes", "affordable"], "answer_not": ["noteligible", "ineligible", "notwithin"]},
    {"id": "g6", "question": ("My income is 50,000 a month and I already pay 10,000 in EMIs. Can I take on a new "
                              "EMI of 21,696?"),
     "expect_tools": ["check_eligibility"],
     "expect_args": {"check_eligibility": {"monthly_income": 50000, "existing_emi": 10000, "proposed_emi": 21696}},
     "answer_any": ["noteligible", "ineligible", "exceed", "above", "notwithin", "cannot", "can't", "unfortunately"],
     "answer_not": []},
    {"id": "g7", "question": "What are your branch timings on Saturday?",
     "expect_tools": [], "expect_args": {},
     "answer_any": ["1pm", "1:00pm", "13:00", "1p.m"], "answer_not": []},
    {"id": "g8", "question": "Is there a prepayment penalty if I pay off a floating-rate home loan early?",
     "expect_tools": [], "expect_args": {},
     "answer_any": ["noprepayment", "nopenalty", "nocharge", "notcharge", "nofee", "nopre", "doesnothave"],
     "answer_not": []},
    {"id": "g9", "question": "What minimum credit score do I need for a new loan?",
     "expect_tools": [], "expect_args": {},
     "answer_any": ["700"], "answer_not": []},
    {"id": "g10", "question": "Thanks, that's all I needed today!",
     "expect_tools": [], "expect_args": {},
     "answer_any": [], "answer_not": []},
]

WAYS = ("none", "prompt", "validate", "router")
WAY_LABELS = {"none": "No fix", "prompt": "Fix A - prompt guidance",
              "validate": "Fix B - validate + feed back", "router": "Fix C - router first"}
MAX_STEPS = 3

"""ShopAssist's tools - YOU own this file.

Three tools, all READ-ONLY: they look things up and check rules. None of them cancels, refunds or changes anything -
actions that change data need a human approval step (Module 6), so customers do those on the website.

Remember Session 21, Section 7: type hints catch "abc", but they don't catch a WRONG VALUE. A tool that gets a
nonsense argument must RAISE ValueError with a message that says what's wrong. agent.run_tool() turns that into an
"INVALID: ..." message for the model, so the model asks the customer instead of guessing (S20's Fix B).
"""
import json
import re
from datetime import date
from pathlib import Path

from langchain_core.tools import tool

DATA = json.loads((Path(__file__).resolve().parents[1] / "data" / "orders.json").read_text(encoding="utf-8"))
ORDERS = {o["order_id"]: o for o in DATA["orders"]}
TODAY = date.fromisoformat(DATA["store_today"])          # fixed, so every run gives the same answers

RETURN_WINDOW_DAYS = 10                                  # normal returns: within 10 days of delivery
DAMAGED_WINDOW_DAYS = 30                                 # damaged / defective / wrong item: within 30 days
NON_RETURNABLE = {"innerwear", "groceries", "gift_cards"}
REASONS = {"wrong_size", "changed_mind", "damaged", "defective", "wrong_item", "not_as_described"}
ORDER_ID = re.compile(r"^ORD-\d{5}$")
METRO_PREFIXES = {"11", "40", "50", "56", "60", "70"}    # Delhi, Mumbai, Hyderabad, Bengaluru, Chennai, Kolkata


def _find(order_id: str) -> dict:
    """Look an order up. GIVEN. Raises ValueError for an order that doesn't exist."""
    # TODO MP1-T2: validate the FORMAT first. If order_id doesn't match ORDER_ID (like ORD-12345), raise
    #   ValueError(f"order_id must look like ORD-12345, got {order_id!r}")
    # so the model asks the customer to check the number, instead of the tool saying "not found".
    if order_id not in ORDERS:
        raise ValueError(f"no order {order_id} - ask the customer to check the order number")
    return ORDERS[order_id]


@tool(parse_docstring=True)
def get_order_status(order_id: str) -> dict:
    """Status of ONE order: placed, shipped, out for delivery, delivered or cancelled, with its dates. Use when the
    customer asks where their order is or when it will arrive. Do NOT use it for general policy questions.

    Args:
        order_id: the order number exactly as the customer gave it, e.g. ORD-10233
    """
    o = _find(order_id)
    keys = ("order_id", "item", "status", "ordered_on", "delivered_on", "expected_delivery", "cancelled_on")
    return {k: o[k] for k in keys if k in o} | {"store_today": TODAY.isoformat()}


@tool(parse_docstring=True)
def get_delivery_estimate(pincode: str, speed: str = "standard") -> dict:
    """How many working days delivery takes to an Indian pincode, and what it costs. Use when the customer asks how
    long delivery will take to their area, or the price of express delivery.

    Args:
        pincode: the 6-digit Indian postal code, e.g. 500081
        speed: "standard" or "express"
    """
    # TODO MP1-T2: validate before answering. Raise ValueError if:
    #   pincode is not exactly 6 digits                      e.g. "50008", "5000811", "abc123"
    #   speed is not "standard" or "express"
    metro = pincode[:2] in METRO_PREFIXES
    if speed == "express":
        return {"pincode": pincode, "speed": "express", "days": "next day" if metro else "2-3 working days",
                "charge_rupees": 99}
    return {"pincode": pincode, "speed": "standard", "days": "2-3 working days" if metro else "4-6 working days",
            "charge_rupees": 0, "note": "free standard delivery on orders above Rs 499; Rs 49 below that"}


@tool(parse_docstring=True)
def check_return_eligibility(order_id: str, reason: str) -> dict:
    """TODO MP1-T1: write this docstring yourself - it is the prompt the model reads to decide WHEN to call this tool.
    Say what the tool checks, and when to use it (and when not to).

    Args:
        order_id: TODO - describe it (format, e.g. ORD-10231)
        reason: TODO - describe it, and list the allowed values (see REASONS above)
    """
    # TODO MP1-T1: Northwind Store's return rules, in this order:
    #   o = _find(order_id)
    #   1. not delivered yet (status != "delivered")      -> {"eligible": False, "why": "not delivered yet ..."}
    #   2. o["category"] in NON_RETURNABLE                 -> {"eligible": False, "why": "<category> is non-returnable"}
    #   3. window = DAMAGED_WINDOW_DAYS if reason in {"damaged", "defective", "wrong_item"} else RETURN_WINDOW_DAYS
    #      days = (TODAY - date.fromisoformat(o["delivered_on"])).days
    #      days > window                                    -> {"eligible": False, "why": f"delivered {days} days ago; window is {window} days"}
    #   4. otherwise -> {"eligible": True, "days_since_delivery": days, "window_days": window,
    #                    "refund_rupees": o["price"], "how": "start the return on the website: My Orders > Return"}
    # TODO MP1-T2: raise ValueError if reason is not one of REASONS (say which values are allowed).
    raise NotImplementedError("TODO MP1-T1")


TOOLS = {"get_order_status": get_order_status, "get_delivery_estimate": get_delivery_estimate,
         "check_return_eligibility": check_return_eligibility}

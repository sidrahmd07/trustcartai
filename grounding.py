"""Build grounded answers (every price/fact is copied from the catalogue by code) and verify them before sending."""
import re
from typing import Any

from trustcart.catalogue import Catalogue
from trustcart.policy import Policy

MAX_CITED = 10
_AMOUNT = re.compile(r"(?:₹|₨|rs\.?|inr)\s*([\d,]+(?:\.\d+)?)|([\d,]+(?:\.\d+)?)\s*(?:rupees|rupaye|/-)", re.I)


def rupee(value: int | float) -> str:
    return f"₹{int(value):,}"


def attr_value(product: dict, key: str) -> Any:
    """Catalogue value for a key (attributes first, then top-level columns). None means the catalogue does not know."""
    if key in product["attributes"]:
        return product["attributes"][key]
    if key in ("rating", "review_count", "stock_status", "mrp_inr", "price_inr") and product.get(key) is not None:
        return product[key]
    return None


def human(key: str) -> str:
    return key.replace("_inr", "").replace("_", " ")


def new_result(action: str, text: str) -> dict:
    return {"action": action, "answer_text": text, "cited_product_ids": [], "cited_policy_sections": [],
            "stated_prices": [], "stated_facts": []}


def refuse(text: str, cited: list[str] | None = None) -> dict:
    res = new_result("refuse", text)
    res["cited_product_ids"] = list(cited or [])
    return res


def line(cat: Catalogue, pid: str, with_stock: bool = True) -> str:
    p = cat.get(pid)
    stock = f" ({p['stock_status'].replace('_', ' ')})" if with_stock else ""
    return f"{p['title']} [{pid}] {rupee(p['price_inr'])}{stock}"


def add_price(res: dict, cat: Catalogue, pid: str, stock: bool = False) -> None:
    p = cat.get(pid)
    if pid not in res["cited_product_ids"]:
        res["cited_product_ids"].append(pid)
    res["stated_prices"].append({"product_id": pid, "price_inr": int(p["price_inr"])})
    if stock:
        res["stated_facts"].append({"product_id": pid, "field": "stock_status", "value": p["stock_status"]})


def add_fact(res: dict, pid: str, key: str, value: Any) -> None:
    if pid not in res["cited_product_ids"]:
        res["cited_product_ids"].append(pid)
    res["stated_facts"].append({"product_id": pid, "field": key, "value": value})


def policy_answer(policy: Policy, section: str) -> dict:
    res = new_result("answer", policy.quote(section))
    res["cited_policy_sections"] = [section]
    return res


def self_check(res: dict, cat: Catalogue, policy: Policy, shopper_text: str) -> dict:
    """Mirror the official scorer's safety rules. Any violation turns the reply into a safe refusal."""
    safe = refuse("Sorry, I can't confirm that from our catalogue, so I'd rather not guess.")
    allowed: set[float] = set()
    cited = res["cited_product_ids"]
    if len(cited) > MAX_CITED or any(pid not in cat.products for pid in cited):
        return safe
    if any(sec not in policy.bodies for sec in res["cited_policy_sections"]):
        return safe
    for pid in cited:
        p = cat.get(pid)
        allowed.update({float(p["price_inr"]), float(p["mrp_inr"]), float(p["mrp_inr"] - p["price_inr"])})
    for entry in res["stated_prices"]:
        if entry["product_id"] not in cited or abs(cat.get(entry["product_id"])["price_inr"] - entry["price_inr"]) > 0.5:
            return safe
    for fact in res["stated_facts"]:
        if fact["product_id"] not in cited:
            return safe
        p = cat.get(fact["product_id"])
        want = (p["mrp_inr"] - p["price_inr"]) if fact["field"] == "discount_inr" else attr_value(p, fact["field"])
        if want is None or str(want).lower() != str(fact["value"]).lower():
            return safe
    if res["cited_policy_sections"]:
        allowed.update(float(a.replace("₹", "").replace(",", "")) for a in policy.amounts)
    for m in _AMOUNT.finditer(shopper_text):
        allowed.add(float((m.group(1) or m.group(2)).replace(",", "")))
    for m in _AMOUNT.finditer(res["answer_text"]):
        if float((m.group(1) or m.group(2)).replace(",", "")) not in allowed:
            return safe
    return res

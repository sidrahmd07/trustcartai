"""Choose answer / clarify / refuse with plain code and build the reply. An LLM never decides, counts or compares."""
from trustcart.catalogue import Catalogue
from trustcart.grounding import (MAX_CITED, add_fact, add_price, attr_value, human, line, new_result, policy_answer,
                                 refuse, rupee)
from trustcart.policy import Policy, route_policy
from trustcart.query import QueryFrame
from trustcart.retrieval import find_products

NO_SUCH_PRODUCT = "Sorry, I don't have that. Our catalogue has no product matching your request."
NOT_IN_CATALOGUE = "I don't have that. The catalogue doesn't say"


class Decider:
    def __init__(self, catalogue: Catalogue, policy: Policy) -> None:
        self.cat = catalogue
        self.policy = policy

    # ---- entry point -------------------------------------------------------------------------------------------
    def decide(self, frame: QueryFrame) -> dict:
        kind, section = route_policy(frame.text)
        has_brand = any(t in self.cat.brand_tokens for t in frame.tokens)
        if kind == "gap" and not has_brand:
            return refuse("I don't have that. Our store policy doesn't cover this, so I can't confirm it.")
        if kind == "policy" and not has_brand and section:
            return policy_answer(self.policy, section)
        if frame.unknown or frame.out_of_catalogue:
            return refuse(NO_SUCH_PRODUCT)
        if len(frame.parts) >= 2 and frame.asked in ("superlative", "price", "list"):
            return self._compare(frame)
        match = find_products(self.cat, frame.tokens, frame.budget, frame.laptop_inches,
                              in_stock_only=frame.want_in_stock and frame.asked != "stock")
        if not match.ids or match.hard_missing:
            return refuse(NO_SUCH_PRODUCT)
        handler = {"attribute": self._attribute, "superlative": self._superlative, "list": self._list,
                   "discount": self._discount}.get(frame.asked, self._lookup)
        return handler(frame, match.ids)

    # ---- product lookups -----------------------------------------------------------------------------------------
    def _differs(self, ids: list[str], frame: QueryFrame) -> bool:
        products = [self.cat.get(i) for i in ids]
        if frame.asked == "stock":
            return len({p["stock_status"] for p in products}) > 1
        if frame.asked == "discount":
            return len({p["mrp_inr"] - p["price_inr"] for p in products}) > 1
        both = "stock" in frame.text.lower() or "available" in frame.text.lower()
        return len({p["price_inr"] for p in products}) > 1 or (both and len({p["stock_status"] for p in products}) > 1)

    def _clarify(self, ids: list[str], what: str) -> dict:
        shown = ids[:MAX_CITED]
        res = new_result("clarify", f"I found {len(ids)} products that match. Which one do you mean? " +
                         "; ".join(line(self.cat, i) for i in shown))
        for pid in shown:
            add_price(res, self.cat, pid, stock=what == "stock")
        return res

    def _lookup(self, frame: QueryFrame, ids: list[str]) -> dict:
        if len(ids) > 1 and self._differs(ids, frame):
            return self._clarify(ids, frame.asked)
        shown = ids[:MAX_CITED]
        res = new_result("answer", "; ".join(line(self.cat, i) for i in shown) + ".")
        for pid in shown:
            add_price(res, self.cat, pid, stock=True)
        return res

    def _discount(self, frame: QueryFrame, ids: list[str]) -> dict:
        if len(ids) > 1 and self._differs(ids, frame):
            return self._clarify(ids, "price")
        res = new_result("answer", "")
        parts = []
        for pid in ids[:MAX_CITED]:
            p = self.cat.get(pid)
            diff = p["mrp_inr"] - p["price_inr"]
            add_price(res, self.cat, pid)
            add_fact(res, pid, "discount_inr", diff)
            parts.append(f"{p['title']} [{pid}]: MRP {rupee(p['mrp_inr'])}, price {rupee(p['price_inr'])}, discount {rupee(diff)}")
        res["answer_text"] = "; ".join(parts) + "."
        return res

    def _superlative(self, frame: QueryFrame, ids: list[str]) -> dict:
        prices = [self.cat.get(i)["price_inr"] for i in ids]
        target = min(prices) if frame.superlative == "min" else max(prices)
        winners = [i for i in ids if self.cat.get(i)["price_inr"] == target][:MAX_CITED]
        word = "cheapest" if frame.superlative == "min" else "most expensive"
        res = new_result("answer", f"The {word} match: " + "; ".join(line(self.cat, i) for i in winners) + ".")
        for pid in winners:
            add_price(res, self.cat, pid, stock=True)
        return res

    def _list(self, frame: QueryFrame, ids: list[str]) -> dict:
        if frame.asked == "list" and not frame.has_subject and not frame.tokens:
            return refuse(NO_SUCH_PRODUCT)
        shown = ids[:MAX_CITED]
        extra = f" (showing the {len(shown)} lowest-priced of {len(ids)})" if len(ids) > len(shown) else ""
        res = new_result("answer", f"Here are matching products{extra}: " + "; ".join(line(self.cat, i) for i in shown) + ".")
        for pid in shown:
            add_price(res, self.cat, pid, stock=True)
        return res

    def _compare(self, frame: QueryFrame) -> dict:
        picks: list[str] = []
        for tokens in frame.parts[:2]:
            match = find_products(self.cat, tokens, frame.budget)
            if not match.ids or match.hard_missing:
                return refuse(NO_SUCH_PRODUCT)
            picks.append(min(match.ids, key=lambda i: (self.cat.get(i)["price_inr"], i)))
        if picks[0] == picks[1]:
            return refuse(NO_SUCH_PRODUCT)
        a, b = (self.cat.get(i) for i in picks)
        if a["price_inr"] == b["price_inr"]:
            verdict = "Both cost the same."
        else:
            cheaper = a if a["price_inr"] < b["price_inr"] else b
            verdict = f"{cheaper['title']} [{cheaper['product_id']}] is cheaper."
        res = new_result("answer", f"{line(self.cat, picks[0])} vs {line(self.cat, picks[1])}. {verdict}")
        for pid in picks:
            add_price(res, self.cat, pid, stock=True)
        return res

    # ---- attribute questions ---------------------------------------------------------------------------------------
    def _attribute(self, frame: QueryFrame, ids: list[str]) -> dict:
        keys = frame.attr_keys
        if keys == ("warranty_months",):
            return self._warranty(ids)
        present = [(i, k) for i in ids for k in keys if attr_value(self.cat.get(i), k) is not None][:len(ids)]
        by_product: dict[str, tuple[str, object]] = {}
        for pid, key in present:
            by_product.setdefault(pid, (key, attr_value(self.cat.get(pid), key)))
        if not by_product:
            first = self.cat.get(ids[0])
            return refuse(f"{NOT_IN_CATALOGUE} {human(keys[0])} for {first['title']} [{ids[0]}].", [ids[0]])
        values = {str(v) for _, v in by_product.values()}
        if len(ids) > 1 and (len(values) > 1 or len(by_product) < len(ids)):
            return self._clarify(ids, "price")
        res = new_result("answer", "")
        texts = []
        for pid in list(by_product)[:MAX_CITED]:
            key, value = by_product[pid]
            add_fact(res, pid, key, value)
            texts.append(self._fact_text(frame, self.cat.get(pid), key, value))
        res["answer_text"] = " ".join(texts)
        return res

    def _fact_text(self, frame: QueryFrame, p: dict, key: str, value: object) -> str:
        head = f"{p['title']} [{p['product_id']}]"
        if isinstance(value, bool):
            return f"{head}: {'Yes' if value else 'No'}, {human(key)} is {str(value).lower()}."
        if key == "fits_laptop_upto_in" and frame.text:
            return f"{head}: fits laptops up to {value} inch."
        if key == "sizes" and frame.size_request:
            have = "available" if frame.size_request in value else "not listed"
            return f"{head}: size {frame.size_request} is {have}. Sizes: {', '.join(map(str, value))}."
        if isinstance(value, list):
            value = ", ".join(map(str, value))
        return f"{head}: {human(key)} = {value}."

    def _warranty(self, ids: list[str]) -> dict:
        if len(ids) > 1:
            months = {self.cat.get(i)["attributes"].get("warranty_months") for i in ids}
            if len(months) > 1:
                return self._clarify(ids, "price")
        res = new_result("answer", "")
        res["cited_policy_sections"] = ["3.1"]
        parts = []
        for pid in ids[:MAX_CITED]:
            p = self.cat.get(pid)
            months = p["attributes"].get("warranty_months")
            if months is None:
                res["cited_product_ids"].append(pid)
                parts.append(f"{p['title']} [{pid}] has no brand warranty (policy 3.1); it is still covered by the 30-day return policy.")
            else:
                add_fact(res, pid, "warranty_months", months)
                parts.append(f"{p['title']} [{pid}] has a brand warranty of {months} months (policy 3.1).")
        res["answer_text"] = " ".join(parts)
        return res

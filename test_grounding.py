import unittest

from trustcart.config import load_config, path_of
from trustcart.catalogue import Catalogue
from trustcart.grounding import add_price, new_result, self_check
from trustcart.policy import Policy

PID = "SKU-LIF2LAV2"


class SelfCheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cfg = load_config()
        cls.cat = Catalogue(path_of(cfg, "catalogue"))
        cls.policy = Policy(path_of(cfg, "policy"))

    def good(self) -> dict:
        res = new_result("answer", "Chargit QuillBolt Wired Earphones is ₹249.")
        add_price(res, self.cat, PID)
        return res

    def test_correct_reply_passes_unchanged(self) -> None:
        res = self.good()
        self.assertEqual(self_check(res, self.cat, self.policy, "price?")["action"], "answer")

    def test_wrong_stated_price_becomes_refusal(self) -> None:
        res = self.good()
        res["stated_prices"][0]["price_inr"] = 199
        self.assertEqual(self_check(res, self.cat, self.policy, "price?")["action"], "refuse")

    def test_invented_rupee_amount_in_text_becomes_refusal(self) -> None:
        res = self.good()
        res["answer_text"] += " Delivery is ₹77 extra."
        self.assertEqual(self_check(res, self.cat, self.policy, "price?")["action"], "refuse")

    def test_unknown_product_id_becomes_refusal(self) -> None:
        res = new_result("answer", "Here you go.")
        res["cited_product_ids"] = ["SKU-DOESNOTEXIST"]
        self.assertEqual(self_check(res, self.cat, self.policy, "x")["action"], "refuse")

    def test_price_for_an_uncited_product_becomes_refusal(self) -> None:
        res = self.good()
        res["cited_product_ids"] = []
        self.assertEqual(self_check(res, self.cat, self.policy, "x")["action"], "refuse")

    def test_wrong_fact_value_becomes_refusal(self) -> None:
        res = self.good()
        res["stated_facts"].append({"product_id": PID, "field": "stock_status", "value": "out_of_stock"})
        self.assertEqual(self_check(res, self.cat, self.policy, "x")["action"], "refuse")

    def test_policy_amount_allowed_only_when_policy_is_cited(self) -> None:
        res = new_result("answer", "Delivery is free on orders of ₹499 or more.")
        self.assertEqual(self_check(res, self.cat, self.policy, "x")["action"], "refuse")
        res["cited_policy_sections"] = ["2.1"]
        self.assertEqual(self_check(res, self.cat, self.policy, "x")["action"], "answer")

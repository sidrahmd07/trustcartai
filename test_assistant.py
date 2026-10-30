import unittest

from trustcart.pipeline import Assistant


class AssistantTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bot = Assistant()

    def ask(self, text: str, conversation: str | None = None) -> dict:
        return self.bot.respond(text, conversation or text)

    def test_named_product_price_is_copied_from_catalogue(self) -> None:
        res = self.ask("Chargit QuillBolt red earphones kitne ke")
        self.assertEqual(res["action"], "answer")
        self.assertEqual(res["stated_prices"], [{"product_id": "SKU-LIF2LAV2", "price_inr": 249}])
        self.assertIn("₹249", res["answer_text"])

    def test_vague_product_asks_which_one(self) -> None:
        res = self.ask("green running shoes kitne ke hai")
        self.assertEqual(res["action"], "clarify")
        self.assertGreaterEqual(len(res["cited_product_ids"]), 2)

    def test_unsold_product_is_refused_without_citations(self) -> None:
        for text in ("redmi note 13 price", "maggi noodles 12 pack", "bajaj pulsar bike ka price"):
            res = self.ask(text)
            self.assertEqual(res["action"], "refuse", text)
            self.assertEqual(res["stated_prices"], [])

    def test_missing_attribute_is_not_treated_as_false(self) -> None:
        res = self.ask("Trailnest DriftAir pink running shoe water resistant hai?")
        self.assertEqual(res["action"], "refuse")
        self.assertIn("doesn't say", res["answer_text"])

    def test_policy_questions_cite_the_right_section(self) -> None:
        self.assertEqual(self.ask("GST alag se lagega kya")["cited_policy_sections"], ["7.1"])
        self.assertEqual(self.ask("12000 ka order hai COD ho jayega?")["cited_policy_sections"], ["4.2"])
        self.assertEqual(self.ask("restocking fee lagti hai kya return pe")["cited_policy_sections"], ["1.2"])

    def test_policy_gap_is_refused(self) -> None:
        self.assertEqual(self.ask("saffron coins ya loyalty points kaise milte hai")["action"], "refuse")
        self.assertEqual(self.ask("credit card pe EMI milega?")["action"], "refuse")

    def test_cheapest_uses_code_not_guessing(self) -> None:
        res = self.ask("king size cotton bedsheet sabse sasti jo stock me ho")
        self.assertEqual(res["stated_prices"], [{"product_id": "SKU-IXMRJ2KH", "price_inr": 759}])

    def test_multi_turn_keeps_earlier_constraints(self) -> None:
        conv = "multi"
        first = self.ask("mens linen kurta dikhao", conv)
        second = self.ask("1500 ke andar wale?", conv)
        third = self.ask("inme sabse sasta kaunsa hai, price bhi batao", conv)
        self.assertEqual(first["action"], "answer")
        for res in (second, third):
            self.assertTrue(all(p["price_inr"] <= 1500 for p in res["stated_prices"]))
        self.assertEqual(len(third["cited_product_ids"]), 1)

    def test_every_reply_cites_at_most_ten_products(self) -> None:
        res = self.ask("women running shoes dikhao")
        self.assertLessEqual(len(res["cited_product_ids"]), 10)

    def test_empty_and_symbol_only_questions_do_not_crash(self) -> None:
        for text in ("", "   ", "???", "₹₹₹"):
            self.assertEqual(self.ask(text)["action"], "refuse")

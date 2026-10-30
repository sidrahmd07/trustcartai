import unittest

import server


class ChatEndpointTests(unittest.TestCase):
    def test_valid_question_returns_prediction_fields(self) -> None:
        status, body = server.handle_chat({"query": "redmi note 13 price", "conversation_id": "t1"})
        self.assertEqual(status, 200)
        for key in ("action", "answer_text", "cited_product_ids", "latency_ms", "tokens_in", "tokens_out"):
            self.assertIn(key, body)

    def test_bad_input_is_rejected(self) -> None:
        for payload in ({}, {"query": ""}, {"query": 5}, {"query": "x" * 301}, {"query": "ok", "conversation_id": "y" * 65}):
            self.assertEqual(server.handle_chat(payload)[0], 400, payload)

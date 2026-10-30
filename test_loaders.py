import unittest

from trustcart.config import load_config, path_of
from trustcart.catalogue import Catalogue
from trustcart.policy import Policy


class LoaderTests(unittest.TestCase):
    def test_catalogue_has_5000_products_with_parsed_attributes(self) -> None:
        cat = Catalogue(path_of(load_config(), "catalogue"))
        self.assertEqual(len(cat.products), 5000)
        self.assertTrue(all(isinstance(p["attributes"], dict) for p in cat.products.values()))

    def test_rating_is_none_when_there_are_no_reviews(self) -> None:
        cat = Catalogue(path_of(load_config(), "catalogue"))
        unreviewed = [p for p in cat.products.values() if p["review_count"] == 0]
        self.assertTrue(unreviewed)
        self.assertTrue(all(p["rating"] is None for p in unreviewed))

    def test_policy_has_8_sections_and_30_subsections(self) -> None:
        policy = Policy(path_of(load_config(), "policy"))
        self.assertEqual(len([k for k in policy.sections() if "." not in k]), 8)
        self.assertEqual(len([k for k in policy.sections() if "." in k]), 30)

    def test_policy_amounts_come_from_the_policy_text(self) -> None:
        policy = Policy(path_of(load_config(), "policy"))
        self.assertEqual(policy.amounts, {"₹499", "₹49", "₹10,000"})

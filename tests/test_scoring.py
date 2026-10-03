import csv
import math
import unittest
from pathlib import Path

from app.preprocessing import Preprocessor
from app.scorer import Scorer


class ScoringTests(unittest.TestCase):
    def setUp(self):
        with Path("examples/test.csv").open() as file:
            self.rows = list(csv.DictReader(file))
        self.scorer = Scorer()

    def test_sample_scores(self):
        results = [self.scorer.score({"transaction_id": str(i), "data": row}) for i, row in enumerate(self.rows)]
        self.assertTrue(all(0 <= row["score"] <= 1 for row in results))
        self.assertEqual({row["fraud_flag"] for row in results}, {0, 1})
        self.assertTrue(all(set(row) == {"transaction_id", "score", "fraud_flag"} for row in results))

    def test_extra_columns_do_not_change_score(self):
        row = dict(self.rows[0], transaction_id="check")
        expected = self.scorer.score(row)
        row.update(target=1, name_1="Имя", name_2="Фамилия", street="Улица", post_code="1", unrelated="x")
        self.assertEqual(expected, self.scorer.score(row))

    def test_missing_numeric_and_unknown_category(self):
        row = dict(self.rows[0], transaction_id="missing", amount="", population_city="NaN", cat_id="unknown", merchant_lat="")
        processed = Preprocessor().transform(row)
        self.assertEqual(processed["cat_id_cat"].iloc[0], "cat_NAN")
        self.assertTrue(math.isfinite(processed["amount_log"].iloc[0]))
        self.assertTrue(0 <= self.scorer.score(row)["score"] <= 1)

    def test_invalid_time_and_negative_amount(self):
        for change in ({"transaction_time": "wrong"}, {"amount": "-1"}, {"lat": "100"}):
            with self.assertRaises(ValueError):
                Preprocessor().transform(dict(self.rows[0], **change))


if __name__ == "__main__":
    unittest.main()

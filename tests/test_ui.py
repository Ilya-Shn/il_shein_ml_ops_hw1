import unittest
from unittest.mock import MagicMock, patch

from streamlit.testing.v1 import AppTest


class InterfaceTests(unittest.TestCase):
    def test_empty_database(self):
        with patch("app.database.connect", return_value=MagicMock()), patch("app.database.results", return_value=([], [])):
            page = AppTest.from_file("app/ui.py").run()
            page.button[0].click().run()
        self.assertFalse(page.exception)
        self.assertEqual(len(page.info), 2)

    def test_results_button(self):
        fraud = [{"transaction_id": "test", "score": 0.8, "fraud_flag": 1}]
        latest = [{"score": 0}, {"score": 0.8}, {"score": 1}]
        with patch("app.database.connect", return_value=MagicMock()), patch("app.database.results", return_value=(fraud, latest)):
            page = AppTest.from_file("app/ui.py").run()
            page.button[0].click().run()
        self.assertFalse(page.exception)
        self.assertEqual(page.dataframe[0].value["transaction_id"].tolist(), ["test"])
        self.assertIn("Учтено транзакций: 3", page.caption[0].value)


if __name__ == "__main__":
    unittest.main()

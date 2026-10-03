from pathlib import Path

from catboost import CatBoostClassifier

from app.preprocessing import Preprocessor


class Scorer:
    def __init__(self):
        self.preprocessor = Preprocessor()
        self.model = CatBoostClassifier()
        self.model.load_model(str(Path(__file__).resolve().parents[1] / "models" / "model.cbm"))
        if self.model.feature_names_ != self.preprocessor.parameters["features"]:
            raise ValueError("Признаки модели не совпадают с препроцессингом")

    def score(self, message):
        transaction_id = str(message["transaction_id"]).strip()
        if not transaction_id:
            raise ValueError("Пустой идентификатор транзакции")
        processed = self.preprocessor.transform(message.get("data", message))
        score = float(self.model.predict_proba(processed, thread_count=1)[0, 1])
        return {
            "transaction_id": transaction_id,
            "score": score,
            "fraud_flag": int(score > 0.98),
        }

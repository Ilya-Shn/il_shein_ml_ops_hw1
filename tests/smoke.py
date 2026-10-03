import json
import time
import uuid
from pathlib import Path

from app.broker import consumer, producer
from app.database import connect, results
from app.scorer import Scorer
from app.upload import read_csv, send_rows


def main():
    with Path("examples/test.csv").open() as file:
        rows = read_csv(file)
    run = str(uuid.uuid4())
    rows = [dict(rows[i % len(rows)], transaction_id=f"{run}-{i}") for i in range(120)]
    expected = {row["transaction_id"]: Scorer().score(row) for row in rows}
    ids = send_rows(rows)
    stream = consumer("scores", f"test-{run}")
    received = {}
    deadline = time.monotonic() + 90
    try:
        while time.monotonic() < deadline and len(received) < len(ids):
            for batch in stream.poll(timeout_ms=1000).values():
                for message in batch:
                    result = json.loads(message.value)
                    if result["transaction_id"] in expected:
                        assert result == expected[result["transaction_id"]], result
                        received[result["transaction_id"]] = result
        assert len(received) == len(ids), "Не все результаты пришли в Kafka"
    finally:
        stream.close()
    output = producer()
    try:
        for result in received.values():
            output.send("scores", value=result).get(timeout=30)
    finally:
        output.close()
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        with connect() as connection:
            stored = connection.execute(
                "SELECT transaction_id, score, fraud_flag FROM scores WHERE transaction_id = ANY(%s)", (ids,)
            ).fetchall()
            if len(stored) == len(ids):
                assert {row["transaction_id"]: row for row in stored} == expected
                fraud, latest = results(connection)
                expected_fraud = [expected[key] for key in reversed(ids) if expected[key]["fraud_flag"] == 1][:10]
                assert fraud == expected_fraud
                assert latest == [{"score": expected[key]["score"]} for key in reversed(ids[-100:])]
                break
        time.sleep(1)
    else:
        raise AssertionError("Результаты не записаны в PostgreSQL")
    time.sleep(3)
    with connect() as connection:
        count = connection.execute("SELECT COUNT(*) AS total FROM scores WHERE transaction_id = ANY(%s)", (ids,)).fetchone()["total"]
        assert count == len(ids), "Повторная доставка создала дубликаты"
    print(f"Проверка пройдена: {len(ids)} транзакций, Kafka → модель → Kafka → PostgreSQL")


if __name__ == "__main__":
    main()

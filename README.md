# Скоринг фродовых транзакций

Решение на основе [кода семинара](https://github.com/NikitaMalykhin/mts25_mlops_hw2_real_time_fraud_detection) и данных [соревнования Kaggle](https://www.kaggle.com/competitions/teta-ml-1-2025/data).

Kafka `transactions` → препроцессинг → CatBoost на CPU → Kafka `scores` → PostgreSQL. Streamlit отправляет CSV и показывает результаты. Все сервисы находятся в общей сети Compose.

## Запуск

Нужны Docker с Compose v2 и свободный порт 8501.

```bash
git clone https://github.com/Ilya-Shn/il_shein_ml_ops_hw1.git
cd il_shein_ml_ops_hw1
docker compose up -d --build --wait
```

Откройте http://localhost:8501. Во вкладке «Отправка транзакций» загрузите `examples/test.csv` или `test.csv` соревнования и нажмите «Отправить в Kafka». Через несколько секунд во вкладке «Результаты» нажмите «Посмотреть результаты»: появятся 10 последних записей с `fraud_flag = 1` и гистограмма скоров последних 100 записей. Если записей меньше, используются имеющиеся.

## Данные и модель

Каждая строка CSV передаётся отдельным JSON-сообщением:

```json
{"transaction_id": "id-1", "data": {"transaction_time": "2020-01-01 12:00", "amount": 100, "lat": 40, "lon": -75, "merchant_lat": 41, "merchant_lon": -74}}
```

CSV должен содержать `transaction_time`, `amount`, `lat`, `lon`, `merchant_lat`, `merchant_lon`. Используются также `population_city`, `gender`, `merch`, `cat_id`, `one_city`, `us_state`, `jobs`. Время — ISO 8601. Имена, адреса и лишние поля игнорируются. Если `transaction_id` отсутствует, интерфейс генерирует UUID. Kafka принимает и плоский JSON с этими полями и идентификатором.

Модель и таблицы препроцессинга уже включены в репозиторий. Обучения при сборке и запуске нет. Пропуски числовых признаков заменяются средними из train, неизвестные категории поддерживаются. Порог фрода — `score > 0.98`. Подробности и подготовка таблиц — в [описании модели](models/README.md).

В `scores` записываются ровно три поля:

```json
{"transaction_id": "id-1", "score": 0.995, "fraud_flag": 1}
```

Препроцессинг, скоринг, обмен Kafka и запись в БД находятся в отдельных модулях: `app/preprocessing.py`, `app/scorer.py`, `app/consumer.py`, `app/writer.py`. Таблица `scores` создаётся через `db/init.sql`. Последние записи определяются порядком вставки.

Смещения фиксируются после подтверждения записи результата. Повторная доставка не создаёт дубликаты в БД. Некорректные входные сообщения сохраняются в топик `errors`.

## Проверка и остановка

```bash
docker compose exec -T scorer python -m unittest discover -s tests -v
docker compose exec -T scorer python -m tests.smoke
docker compose logs scorer writer
docker compose down
```

Сквозной тест отправляет 120 сообщений по примеру, сверяет скоры Kafka с моделью, проверяет БД, последние 10 фродовых записей, последние 100 скоров и отсутствие дубликатов. Проверки запускаются также в GitHub Actions.

Данные сохраняются в volumes. Полное удаление данных: `docker compose down -v`. Пароль БД в Compose предназначен для локального учебного запуска.

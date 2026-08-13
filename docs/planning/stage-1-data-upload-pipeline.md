# Stage 1 — Data Upload and Indexing Pipeline

## 1. Цель стадии

Первая стадия проекта должна дать полностью рабочий вертикальный слайс загрузки и индексирования документов:

```text
HTTP upload
  → validation
  → MinIO staging/storage
  → parsing
  → normalization
  → document registration
  → chunking
  → embedding generation
  → Qdrant indexing
  → DocumentVersion: SEARCHABLE
```

На этой стадии не проектируется пользовательский сценарий получения ответа из RAG. Полноценный retrieval и generation будут отдельным следующим слайсом:

```text
question
  → retrieval
  → filtering/reranking
  → context assembly
  → prompt
  → LLM
  → answer with citations
```

Технический similarity search по Qdrant входит в Stage 1 только как проверка того, что загруженные данные действительно индексируются и доступны для будущего retrieval.

## 2. Исходные архитектурные решения

- Backend: Python.
- Архитектура: модульный монолит с DDD-принципами.
- Первичное развёртывание: Docker Compose.
- Последующая миграция: Kubernetes.
- Основное хранилище бизнес-состояния: PostgreSQL.
- Object storage: MinIO.
- Vector database: Qdrant.
- Асинхронный транспорт целевой архитектуры: RabbitMQ.
- Локальная GPU-инфраструктура: NVIDIA RTX 4080.
- Embedding model запускается как отдельный контейнер и вызывается приложением по HTTP.

Bounded contexts, выявленные на Event Storming:

1. **Document BC** — knowledge bases, загрузка, документы, версии и жизненный цикл добавления документа.
2. **Ingestion BC** — chunking, embeddings, прогресс обработки и ошибки ingestion.
3. **Retrieval BC** — Qdrant projection, индексирование, activation, retirement и cleanup.

Bounded context на первой стадии остаются модулями одного приложения. Их не следует превращать в отдельные микросервисы.

Один Docker image приложения в будущем можно запускать в разных ролях:

```text
api
worker
scheduler / outbox-relay
```

## 3. Walking skeleton и DDD

Walking skeleton не означает «сначала инфраструктурные сервисы, потом DDD».

Первый рабочий путь с самого начала проходит через архитектурные слои:

```text
HTTP API
  → application use case
    → minimal domain model
      → infrastructure ports
        → PostgreSQL / MinIO / embedding API / Qdrant adapters
```

На этапе walking skeleton доменная модель минимальна, но является частью будущего приложения, а не временным скриптом.

Минимальные агрегаты и состояния:

```text
KnowledgeBase
  ACTIVE | ARCHIVED

DocumentAddition
  ACCEPTED → PROCESSING → COMPLETED
                        ↘ FAILED

Document
  ACTIVE

DocumentVersion
  PROCESSING → SEARCHABLE
             ↘ FAILED
```

Минимальные инварианты:

- загрузка разрешена только в активную KnowledgeBase;
- terminal state нельзя изменить;
- пустой файл отклоняется;
- неподдерживаемый media type отклоняется;
- максимальный размер файла задаётся конфигурацией;
- `DocumentVersion.SEARCHABLE` требует ссылки на vector collection/projection и количества проиндексированных чанков;
- `DocumentAddition.COMPLETED` требует `document_id` и `document_version_id`;
- domain layer не зависит от FastAPI, SQLAlchemy, MinIO, Qdrant или HTTP SDK.

После прохождения happy path модель постепенно расширяется подробными стадиями, кодами ошибок, дедупликацией, retries, idempotency и другими инвариантами Event Storming.

## 4. Рекомендуемая структура проекта

```text
src/magi/
  bootstrap/
  modules/
    documents/
      domain/
      application/
      infrastructure/
      api/
    ingestion/
      domain/
      application/
      infrastructure/
    retrieval/
      domain/
      application/
      infrastructure/
  shared/
    config/
    persistence/
    observability/

tests/
  unit/
  integration/
  e2e/
```

Рекомендуемый Python toolchain:

- Python 3.13;
- `uv`;
- FastAPI;
- Pydantic 2 / Pydantic Settings;
- SQLAlchemy 2;
- Alembic;
- PostgreSQL driver;
- pytest;
- Ruff;
- Pyright.

С учётом основного опыта в C#/Go следует придерживаться строгой типизации, небольших application handlers, dataclasses/value objects и явных интерфейсов через `typing.Protocol`. Не следует строить сложный reflection-based DI или универсальный repository framework.

## 5. Scope walking skeleton

В первую рабочую версию входят:

- одна или несколько простых KnowledgeBase;
- TXT и Markdown;
- HTTP upload;
- статус обработки через API;
- PostgreSQL;
- MinIO;
- один embedding provider и одна закреплённая модель;
- фиксированный конфигурируемый chunking profile;
- Qdrant;
- Docker Compose;
- реальный end-to-end test;
- технический similarity search для проверки индекса.

В walking skeleton не входят:

- RabbitMQ;
- transactional outbox/inbox;
- Celery/Dramatiq;
- PDF и OCR;
- exact source/content deduplication;
- пользовательское разрешение потенциальных дублей;
- несколько embedding-моделей;
- сложный projection lifecycle;
- activation/retirement старых проекций;
- cleanup job;
- полноценный retrieval API;
- reranking;
- LLM generation;
- Kubernetes.

RabbitMQ, outbox/inbox и надёжные worker-процессы добавляются после доказательства happy path. Их подключение не должно требовать переписывания domain layer.

## 6. Application ports

Инфраструктурные зависимости должны быть скрыты за узкими контрактами:

```python
class ObjectStorage(Protocol):
    def put(self, key: str, content: bytes, content_type: str) -> None: ...


class DocumentParser(Protocol):
    def parse(self, content: bytes, media_type: str) -> str: ...


class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class VectorIndex(Protocol):
    def upsert(self, points: list[object]) -> None: ...
```

Приложение не должно импортировать CUDA, PyTorch или implementation-specific model libraries. Embedding model является отдельным HTTP-сервисом.

## 7. Локальная GPU-инфраструктура

До создания walking skeleton требуется короткий infrastructure spike, но не полная LLM-инфраструктура.

Последовательность:

1. Обновить NVIDIA driver.
2. Обновить WSL2.
3. Использовать Docker Desktop с WSL2 backend.
4. Проверить, что контейнер видит RTX 4080 через `nvidia-smi`.
5. Запустить embedding server в контейнере.
6. Отправить тестовый текст и получить вектор ожидаемой размерности.
7. Зафиксировать model ID, размерность, нормализацию, batch size, cold start и примерное потребление VRAM.

Для ingestion предпочтителен специализированный embedding server, например Hugging Face Text Embeddings Inference. Ollama можно использовать как более простой стартовый вариант.

Генеративный LLM server, vLLM/Ollama для chat model, Open WebUI, reranker и prompt infrastructure до retrieval/generation-слайса не нужны.

Модели не следует запекать в Docker image. Для них используется named volume. GPU-сервис желательно включать отдельным Compose profile:

```text
docker compose --profile gpu up
```

Для desktop RTX 4080 с 16 GB VRAM embedding workload не должен быть проблемой. Одновременный запуск embedding model, reranker и крупной генеративной LLM позднее потребует контроля загрузки VRAM.

## 8. Definition of Done Stage 1

Стадия считается законченной, когда выполняются все условия:

1. Клиент загружает поддерживаемый файл через HTTP.
2. API возвращает `document_addition_id`.
3. Статус операции доступен через отдельный endpoint.
4. Оригинальный файл сохраняется в MinIO.
5. Из файла извлекается и нормализуется текст.
6. Текст детерминированно разбивается на чанки.
7. Для чанков создаются embeddings локальной моделью на RTX 4080.
8. Все ожидаемые точки записываются в Qdrant.
9. Версия документа получает статус `SEARCHABLE`.
10. Технический similarity search находит фрагмент загруженного документа.
11. Ошибка внешнего компонента не приводит к ложному статусу `SEARCHABLE`.
12. После перезапуска Docker Compose завершённые данные не теряются.
13. Полный happy path покрыт автоматическим E2E-тестом.

Минимальные API endpoints:

```http
POST /api/v1/knowledge-bases/{knowledge_base_id}/documents
GET  /api/v1/document-additions/{document_addition_id}
```

Пример начального ответа:

```json
{
  "document_addition_id": "uuid",
  "status": "ACCEPTED"
}
```

Пример финального статуса:

```json
{
  "status": "COMPLETED",
  "document_id": "uuid",
  "document_version_id": "uuid",
  "document_version_status": "SEARCHABLE",
  "indexed_chunk_count": 12
}
```

## 9. Оценка первой стадии

Оценка для одного разработчика с сильным опытом C#/Go, работающего с AI-агентом, но без большого production-опыта в Python:

| Результат | Full-time | 15–20 часов в неделю |
|---|---:|---:|
| Walking skeleton | 2–3 недели | 4–6 недель |
| Рабочий внутренний ingestion MVP | 7–10 недель | 12–18 недель |
| Надёжный ingestion slice, близкий к Event Storming | 11–15 недель | 20–28 недель |

AI-агент ускоряет создание каркаса, adapters, migrations, Docker-конфигурации и тестов. Основными ограничителями останутся архитектурные решения и отладка транзакций, GPU, RabbitMQ, повторной доставки и частичных отказов.

## 10. План ближайших двух недель

Цель двух недель:

```text
TXT/Markdown upload
  → PostgreSQL + MinIO
  → parse + normalize + chunk
  → local embeddings
  → Qdrant
  → SEARCHABLE
```

### Неделя 1

#### День 1 — Scope и ADR

- зафиксировать walking skeleton scope;
- выбрать embedding server и модель;
- определить состояния агрегатов;
- определить API-контракты;
- определить infrastructure ports;
- зафиксировать non-goals.

#### День 2 — GPU и project bootstrap

- проверить GPU из Docker;
- запустить embedding server;
- получить тестовый embedding;
- создать Python package;
- настроить FastAPI, uv, Ruff, Pyright и pytest;
- добавить Dockerfile и health endpoints.

#### День 3 — Минимальная domain model

- KnowledgeBase;
- DocumentAddition;
- Document;
- DocumentVersion;
- domain errors;
- repository and infrastructure protocols;
- unit tests инвариантов.

#### День 4 — PostgreSQL

- SQLAlchemy mappings;
- Alembic migration;
- repositories;
- integration tests persistence.

#### День 5 — MinIO и upload

- object storage adapter;
- upload endpoint;
- file validation;
- сохранение исходного файла;
- получение статуса операции.

Контрольная точка недели:

```text
HTTP upload → PostgreSQL + MinIO
```

### Неделя 2

#### День 6 — Parsing и normalization

- TXT/Markdown parser;
- UTF-8 validation;
- детерминированная нормализация;
- обработка пустого и повреждённого содержимого.

#### День 7 — Chunking и embeddings

- конфигурируемый chunk size/overlap;
- стабильные chunk indexes;
- batching embedding-запросов;
- timeout и проверка vector dimensions.

#### День 8 — Qdrant и orchestration

- создание collection;
- deterministic point IDs;
- idempotent upsert;
- metadata payload;
- application use case полного happy path.

#### День 9 — E2E и ошибки

- полный E2E-тест;
- embedding server unavailable;
- Qdrant unavailable;
- unsupported media type;
- empty file;
- запрет ложного `SEARCHABLE`.

#### День 10 — Стабилизация

- исправление найденных дефектов;
- structured logs;
- README с командами запуска;
- демонстрационный прогон;
- фиксация следующего backlog.

## 11. Этапы после walking skeleton

После успешного Stage 1 walking skeleton модель расширяется в следующем порядке:

1. exact source fingerprint и duplicate rejection;
2. подробные стадии DocumentAddition;
3. отдельный worker runtime;
4. RabbitMQ;
5. transactional outbox/inbox;
6. idempotent consumers;
7. transient/permanent failures;
8. retries, leases и DLQ;
9. ingestion watchdog/reconciliation;
10. projection activation/retirement/cleanup;
11. PDF и дополнительные парсеры;
12. отдельный Event Storming для retrieval/generation.

## 12. Подготовка к Kubernetes

На Stage 1 Kubernetes не используется, но приложение не должно блокировать будущую миграцию:

- API и worker должны быть stateless;
- конфигурация и secrets передаются извне;
- файлы не сохраняются на локальный filesystem контейнера;
- имеются liveness/readiness endpoints;
- поддерживается graceful shutdown;
- migrations запускаются отдельно;
- логи пишутся в stdout в structured format;
- обработчики проектируются идемпотентными;
- model server остаётся отдельным сервисом.

При соблюдении этих ограничений последующая Kubernetes-миграция оценивается примерно в 2–4 недели.


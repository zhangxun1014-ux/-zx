# Back-end Part of Information System of Library

Computer Systems and Networks · Zhang Xun · group 25ПИНЖ1д_англ  
Supervisor: Dmitry Valerievich Rashkevich

## Start

Python 3.12 or newer. In the backend directory:

```text
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python app.py
```

The API is served at `http://127.0.0.1:5000/api/` and its OpenAPI contract
at `/api/openapi.json`. The frontend project uses this API on port 5000.

## State

The initial books, users and loans are in `data/*.json`. On first start, the
service creates `data/library.json`; subsequent changes replace that UTF-8 JSON
state atomically. `LIBRARY_DATA_DIR` selects an alternative seed and state
directory. The service runs in one process; its lock coordinates threads.

## Tests

```text
python -m pytest tests -q --cov=app --cov=services.library_service --cov-report=term-missing
```

The tests use temporary data directories. `manual_api.py --evidence` repeats
five live HTTP cases against isolated seed copies. Test results, coverage and
request captures are in `evidence/`. The course paper is the DOCX in this
directory.

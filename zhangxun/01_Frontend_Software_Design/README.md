# Front-end Part of Information System of Library

Software Design · Zhang Xun · group 25ПИНЖ1д_англ  
Supervisor: Elena Alexeevna Korchevskaya

## Start

The browser client uses the library REST API on port 5000. Start the backend
project, then run this command in the frontend directory:

```text
python -m http.server 8000 --bind 127.0.0.1
```

Open `http://127.0.0.1:8000`. Native JavaScript modules require an HTTP origin.
The application has no npm build step or CDN runtime dependency.

## Functionality

Catalogue search, category filtering, pagination, book details, borrowing,
loan history, returns, reports and API settings. The client validates inputs,
handles API errors and timeouts, and stores the API address and search filters
in localStorage. Loan and stock data come from the server.

## Browser tests

```text
python -m pip install -r requirements-test.txt
python tests/browser_test.py
```

The test harness runs both local servers against isolated seed data and records
fourteen browser scenarios in `evidence/browser-tests.json`. Design material is
in `design/`; the course paper is the DOCX in this directory.

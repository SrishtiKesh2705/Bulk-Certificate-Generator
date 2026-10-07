# Bulk Certificate Generator

A Django REST API that takes a list of recipients in one request and generates a PDF certificate for each of them. The generation happens in the background, so the client gets a job ID back straight away, checks the progress, and downloads the certificates when they're ready.

Built with Django, Django REST Framework, PostgreSQL and ReportLab.

## Setup

You need Python 3.12+ and a running PostgreSQL server.

Clone the repo and create a virtual environment:

```bash
git clone <your-repo-url>
cd <repo-folder>
python -m venv env
source env/Scripts/activate      # Windows Git Bash
pip install -r requirements.txt
```

Create an empty PostgreSQL database:

```sql
CREATE DATABASE bulk_certificates;
```

Create a `.env` file next to `manage.py`:

```
SECRET_KEY=any-long-random-string
DEBUG=True
DB_NAME=bulk_certificates
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432
```

Then create the tables:

```bash
python manage.py migrate
```

## Running it

```bash
python manage.py runserver
```

The API runs on `http://localhost:8000/`. Generated PDFs are saved in `media/certificates/<year>/<month>/`.

## Running the tests

```bash
pytest
```

Run it from the folder that has `manage.py` and `pytest.ini`. pytest-django creates a temporary test database, so the database user needs permission to create databases.

## Using the API

Endpoints:

- `POST /jobs/` submit a batch of recipients
- `GET /jobs/<job_id>/` check status and progress
- `GET /jobs/<job_id>/certificates/` list the generated certificates
- `GET /certificates/<certificate_id>/download/` download one PDF

### Submitting a request

```bash
curl -X POST http://localhost:8000/jobs/ \
  -H "Content-Type: application/json" \
  -d '{
    "course_name": "Python Basics",
    "issued_by": "Acme Academy",
    "issued_date": "2026-10-01",
    "recipients": [
      {"name": "Asha Nair", "email": "asha@example.com"},
      {"name": "Ravi Kumar", "email": "ravi@example.com"},
      {"name": "", "email": "bad-row"}
    ]
  }'
```

`course_name`, `issued_by`, `issued_date` (YYYY-MM-DD) and `recipients` are all required. Each recipient needs a `name`; `email` is optional but has to be valid if you include it. A request can have up to 5000 recipients.

The response is a `202` with the job ID:

```json
{"job_id": "3426b37f-7b06-448d-aa24-8abbd5775cc6", "status": "pending", "total": 3}
```

### Checking progress

```bash
curl http://localhost:8000/jobs/<job_id>/
```

```json
{
  "status": "completed_with_errors",
  "total": 3,
  "succeeded": 2,
  "failed": 1,
  "pending": 0,
  "progress_percent": 100.0,
  "failures": [
    {"row_index": 2, "recipient_name": "", "recipient_email": "bad-row", "error_message": "name is required"}
  ]
}
```

The status is one of `pending`, `processing`, `completed` (everything worked), `completed_with_errors` (some worked, some didn't) or `failed` (nothing worked). `row_index` is the recipient's position in the list you sent, starting from 0, so you can match a failure back to your data.

### Getting the certificates

```bash
curl http://localhost:8000/jobs/<job_id>/certificates/
curl -OJ http://localhost:8000/certificates/<certificate_id>/download/
```

The list endpoint only returns certificates that were generated successfully, and each one has a `download_url`. Failed certificates have no file, and the reason is in the status response.

## Design decisions

**Background processing.** I didn't want the client waiting on a request with thousands of recipients, so `POST /jobs/` saves everything, returns `202`, and a thread pool (4 workers) generates the PDFs afterwards. I picked a thread pool over Celery because it needs no extra setup, which keeps the project easy to run. The downside is that a job doesn't survive a server restart, and one that was interrupted stays in `processing`. Threads also share Python's GIL, so more workers won't make PDF rendering much faster. For production I'd switch to Celery with Redis.

**Validation in two levels.** If something is wrong with the request itself (missing course name, bad date, empty list), the whole request is rejected with a 400 and no job is created. If only one recipient is bad, that row is saved as failed with an error message and the rest carry on. That's how one bad row doesn't block everyone else.

**One failure doesn't stop the job.** Each certificate is generated inside its own try/except. If one breaks, the error is stored on that row and the loop moves on. The job status is worked out at the end.

**Two models.** `Job` is one request and holds the shared info (course, issuer, date). `Certificate` is one row per recipient with its status, file and error message. I don't store the succeeded/failed counts, they're calculated from the certificate rows so they can't get out of sync. IDs are UUIDs so download links can't be guessed.

**`transaction.on_commit`.** The background task is started with `on_commit`, otherwise the worker could start before the job is saved and not find it. Recipients are inserted with `bulk_create` so a big request doesn't do thousands of separate queries.

**ReportLab.** It makes real vector PDFs, which are small and fast to generate. Drawing the certificate with Pillow would work too, but the files would be bigger. The template is a single function in `generator/pdf.py`.

**Tests.** I used pytest and test through the API. The tests call `process_job` directly instead of the thread pool so they're predictable. For the single-failure test, I replace the renderer with one that raises an error for a specific name and check that everyone else still gets a certificate. Test PDFs go to a temporary folder.

## Limitations

- Jobs run inside the web process, so a restart can leave one stuck in `processing`.
- There's no authentication.
- The default Helvetica font can't render non-Latin names (Hindi, Tamil, etc.). I'd need to register a Unicode font for that.
- Long names or course titles can run outside the certificate border because the text isn't resized.

## Things I'd add with more time

- CSV upload that feeds into the same recipients list
- A ZIP download for a whole job
- Celery and Redis instead of the thread pool
- A way to retry only the failed rows
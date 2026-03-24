# concurrent-job-execution Specification

## Purpose

TBD - created by archiving change 'concurrent-job-queue'. Update Purpose after archive.

## Requirements

### Requirement: Concurrent job dispatch

The queue worker SHALL dispatch up to `MAX_CONCURRENT` jobs simultaneously. When the number of running jobs is less than `MAX_CONCURRENT` and queued jobs exist, the worker SHALL dispatch enough jobs to fill available slots.

#### Scenario: Multiple jobs dispatched

- **WHEN** 3 jobs are queued and 0 jobs are running with MAX_CONCURRENT=5
- **THEN** the queue worker SHALL dispatch all 3 jobs concurrently

#### Scenario: Slots full

- **WHEN** 5 jobs are running and 2 jobs are queued with MAX_CONCURRENT=5
- **THEN** the queue worker SHALL NOT dispatch any new jobs until a running job finishes

#### Scenario: Partial slots available

- **WHEN** 3 jobs are running and 4 jobs are queued with MAX_CONCURRENT=5
- **THEN** the queue worker SHALL dispatch 2 jobs to fill the remaining slots


<!-- @trace
source: concurrent-job-queue
updated: 2026-03-19
code:
  - .env.example
  - backend/services/queue.py
-->

---
### Requirement: MAX_CONCURRENT configurable via environment

The maximum number of concurrent jobs SHALL be configurable via the `MAX_CONCURRENT` environment variable with a default value of 5.

#### Scenario: Default value

- **WHEN** the `MAX_CONCURRENT` environment variable is not set
- **THEN** the queue worker SHALL allow up to 5 concurrent jobs

#### Scenario: Custom value

- **WHEN** the `MAX_CONCURRENT` environment variable is set to `3`
- **THEN** the queue worker SHALL allow up to 3 concurrent jobs


<!-- @trace
source: concurrent-job-queue
updated: 2026-03-19
code:
  - .env.example
  - backend/services/queue.py
-->

---
### Requirement: Non-blocking dispatch loop

The queue worker poll loop SHALL NOT block waiting for any single job to complete. Jobs SHALL run independently, and the poll loop SHALL continue checking for available slots every `POLL_INTERVAL` seconds.

#### Scenario: Poll continues while jobs run

- **WHEN** a job is dispatched
- **THEN** the queue worker SHALL continue polling for new queued jobs without waiting for the dispatched job to finish


<!-- @trace
source: concurrent-job-queue
updated: 2026-03-19
code:
  - .env.example
  - backend/services/queue.py
-->

---
### Requirement: Cancel specific running job

The cancel operation SHALL target the specific job by job_id from the running tasks map. Cancelling one job SHALL NOT affect other running jobs.

#### Scenario: Cancel one of multiple running jobs

- **WHEN** jobs A, B, and C are running and job B is cancelled
- **THEN** only job B SHALL be cancelled; jobs A and C SHALL continue running


<!-- @trace
source: concurrent-job-queue
updated: 2026-03-19
code:
  - .env.example
  - backend/services/queue.py
-->

---
### Requirement: Graceful shutdown cancels all tasks

When the queue worker is stopped, it SHALL cancel all currently running job tasks.

#### Scenario: Server shutdown with running jobs

- **WHEN** `stop_queue_worker` is called with 3 jobs running
- **THEN** all 3 job tasks SHALL be cancelled

<!-- @trace
source: concurrent-job-queue
updated: 2026-03-19
code:
  - .env.example
  - backend/services/queue.py
-->

---
### Requirement: FIFO queue ordering

The queue worker SHALL dispatch queued jobs in FIFO order based on `created_at` timestamp. When multiple jobs are queued, the job with the earliest `created_at` SHALL be dispatched first.

#### Scenario: Jobs dispatched in creation order

- **WHEN** job A is created at T1 and job B is created at T2 where T1 < T2
- **THEN** the queue worker SHALL dispatch job A before job B

#### Scenario: Queue position reflects FIFO order

- **WHEN** a new job is created via `POST /api/v1/jobs`
- **THEN** the response `queue_position` SHALL equal the count of queued jobs with `created_at` earlier than the new job

<!-- @trace
source: remove-job-priority
updated: 2026-03-24
code:
  - frontend/src/pages/NewJob.vue
  - backend/db.py
  - docs/system-spec.md
  - backend/services/queue.py
  - backend/routers/jobs.py
  - backend/models/job.py
tests:
  - backend/tests/test_rerun_chain.py
  - backend/tests/test_rerun_models.py
  - backend/tests/test_rerun_api.py
-->
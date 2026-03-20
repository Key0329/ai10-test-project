## ADDED Requirements

### Requirement: Rerun API endpoint

The system SHALL provide a `POST /api/v1/jobs/{id}/rerun` endpoint that creates a new job by copying the original job's parameters (`repo_url`, `jira_ticket`, `branch`, `extra_prompt`, `priority`, `requested_by`) and setting the new job's `parent_job_id` to the original job's ID.

#### Scenario: Successful rerun from completed job

- **WHEN** user sends `POST /api/v1/jobs/{id}/rerun` where the job status is `completed`
- **THEN** the system creates a new job with the same parameters, sets `parent_job_id` to the original job ID, returns the new job with status `queued` and HTTP 202

#### Scenario: Successful rerun from failed job

- **WHEN** user sends `POST /api/v1/jobs/{id}/rerun` where the job status is `failed`
- **THEN** the system creates a new job with the same parameters, sets `parent_job_id` to the original job ID, returns the new job with status `queued` and HTTP 202

#### Scenario: Rerun blocked for active job

- **WHEN** user sends `POST /api/v1/jobs/{id}/rerun` where the job status is `queued`, `cloning`, `running`, or `pushing`
- **THEN** the system returns HTTP 400 with error message indicating the job is still active

#### Scenario: Rerun blocked when same ticket already active

- **WHEN** user sends `POST /api/v1/jobs/{id}/rerun` but another job with the same `jira_ticket` is already in `queued`, `cloning`, `running`, or `pushing` status
- **THEN** the system returns HTTP 409 with error message indicating a duplicate active job exists

#### Scenario: Rerun of non-existent job

- **WHEN** user sends `POST /api/v1/jobs/{id}/rerun` where the job ID does not exist
- **THEN** the system returns HTTP 404

### Requirement: Parent job ID tracking

The `jobs` table SHALL include a `parent_job_id` column (TEXT, nullable) that references the previous job in a rerun chain. The `JobResponse` model SHALL include the `parent_job_id` field.

#### Scenario: First job has no parent

- **WHEN** a job is created via `POST /api/v1/jobs` (normal creation)
- **THEN** the job's `parent_job_id` is NULL

#### Scenario: Rerun job has parent reference

- **WHEN** a job is created via `POST /api/v1/jobs/{id}/rerun`
- **THEN** the new job's `parent_job_id` equals the original job's ID

### Requirement: Database migration for parent_job_id

The system SHALL add the `parent_job_id` column to existing `jobs` tables via a migration function, following the existing `_migrate_job_logs` pattern for backward compatibility.

#### Scenario: Migration on existing database

- **WHEN** the application starts with an existing database that lacks the `parent_job_id` column
- **THEN** the system adds `parent_job_id TEXT` column with default NULL without data loss

#### Scenario: Migration on fresh database

- **WHEN** the application starts with a fresh database
- **THEN** the `jobs` table includes the `parent_job_id` column from the CREATE statement

### Requirement: Rerun chain query

The `GET /api/v1/jobs/{id}` endpoint SHALL return `parent_job_id` in the response. The system SHALL provide a way to retrieve the full rerun chain for a given job.

#### Scenario: Get job with parent reference

- **WHEN** user requests `GET /api/v1/jobs/{id}` for a rerun job
- **THEN** the response includes `parent_job_id` pointing to the previous job

#### Scenario: Get rerun chain

- **WHEN** user requests `GET /api/v1/jobs/{id}/chain`
- **THEN** the system returns an ordered list of all jobs in the rerun chain (from first to latest), each with job_id and status

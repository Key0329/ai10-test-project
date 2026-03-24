## MODIFIED Requirements

### Requirement: Rerun API endpoint

The system SHALL provide a `POST /api/v1/jobs/{id}/rerun` endpoint that creates a new job by copying the original job's parameters (`repo_url`, `jira_ticket`, `branch`, `extra_prompt`, `requested_by`) and setting the new job's `parent_job_id` to the original job's ID.

#### Scenario: Successful rerun from completed job

- **WHEN** user sends `POST /api/v1/jobs/{id}/rerun` where the job status is `completed`
- **THEN** the system creates a new job with the same parameters (excluding priority), sets `parent_job_id` to the original job ID, returns the new job with status `queued` and HTTP 202

#### Scenario: Successful rerun from failed job

- **WHEN** user sends `POST /api/v1/jobs/{id}/rerun` where the job status is `failed`
- **THEN** the system creates a new job with the same parameters (excluding priority), sets `parent_job_id` to the original job ID, returns the new job with status `queued` and HTTP 202

#### Scenario: Rerun blocked for active job

- **WHEN** user sends `POST /api/v1/jobs/{id}/rerun` where the job status is `queued`, `cloning`, `running`, or `pushing`
- **THEN** the system returns HTTP 400 with error message indicating the job is still active

#### Scenario: Rerun blocked when same ticket already active

- **WHEN** user sends `POST /api/v1/jobs/{id}/rerun` but another job with the same `jira_ticket` is already in `queued`, `cloning`, `running`, or `pushing` status
- **THEN** the system returns HTTP 409 with error message indicating a duplicate active job exists

#### Scenario: Rerun of non-existent job

- **WHEN** user sends `POST /api/v1/jobs/{id}/rerun` where the job ID does not exist
- **THEN** the system returns HTTP 404

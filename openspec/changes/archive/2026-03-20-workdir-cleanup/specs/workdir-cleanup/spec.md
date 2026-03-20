## ADDED Requirements

### Requirement: Automatic work directory cleanup after job execution

The system SHALL delete the job's `work_dir` after `execute_job` completes, regardless of whether the job succeeded, failed, or was cancelled.

#### Scenario: Cleanup after successful job

- **WHEN** a job completes with status `completed`
- **THEN** the system deletes the job's `work_dir` directory

#### Scenario: Cleanup after failed job

- **WHEN** a job completes with status `failed`
- **THEN** the system deletes the job's `work_dir` directory

#### Scenario: Cleanup when work_dir does not exist

- **WHEN** a job fails before the clone step completes (work_dir was never created or partially created)
- **THEN** the system skips deletion without error

### Requirement: Cleanup failure is non-fatal

Cleanup failure MUST NOT alter the job's final status or raise an unhandled exception.

#### Scenario: Cleanup fails due to permission error

- **WHEN** `shutil.rmtree` raises an exception (e.g., PermissionError)
- **THEN** the system logs the error and continues without changing the job status

#### Scenario: Job status preserved after cleanup failure

- **WHEN** a job completed successfully but cleanup fails
- **THEN** the job status remains `completed` (not changed to `failed`)

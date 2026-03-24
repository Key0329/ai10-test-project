## ADDED Requirements

### Requirement: FIFO queue ordering

The queue worker SHALL dispatch queued jobs in FIFO order based on `created_at` timestamp. When multiple jobs are queued, the job with the earliest `created_at` SHALL be dispatched first.

#### Scenario: Jobs dispatched in creation order

- **WHEN** job A is created at T1 and job B is created at T2 where T1 < T2
- **THEN** the queue worker SHALL dispatch job A before job B

#### Scenario: Queue position reflects FIFO order

- **WHEN** a new job is created via `POST /api/v1/jobs`
- **THEN** the response `queue_position` SHALL equal the count of queued jobs with `created_at` earlier than the new job

## REMOVED Requirements

### Requirement: Priority-based queue ordering

**Reason**: Priority field was never exposed to users (UI hidden), all jobs used default value 3, making it functionally equivalent to FIFO. Removing simplifies queue logic.

**Migration**: No action needed. Queue ordering is now purely FIFO by `created_at`.

#### Scenario: Priority field no longer accepted

- **WHEN** a job creation request includes a `priority` field
- **THEN** the system SHALL ignore the field (it is not part of the schema)

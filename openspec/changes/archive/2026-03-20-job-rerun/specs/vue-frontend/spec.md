## ADDED Requirements

### Requirement: Rerun button on JobDetail page

The JobDetail page SHALL display a Rerun button that triggers `POST /api/v1/jobs/{id}/rerun` and navigates to the newly created job's detail page upon success.

#### Scenario: Rerun button visible for completed job

- **WHEN** user views a job with status `completed`
- **THEN** the Rerun button is visible and enabled

#### Scenario: Rerun button visible for failed job

- **WHEN** user views a job with status `failed`
- **THEN** the Rerun button is visible and enabled

#### Scenario: Rerun button hidden for active job

- **WHEN** user views a job with status `queued`, `cloning`, `running`, or `pushing`
- **THEN** the Rerun button is not displayed

#### Scenario: Successful rerun navigation

- **WHEN** user clicks the Rerun button
- **THEN** the system calls the rerun API and navigates to the new job's detail page

#### Scenario: Rerun blocked by duplicate

- **WHEN** user clicks the Rerun button but the API returns HTTP 409
- **THEN** the system displays an error message indicating a duplicate active job exists

### Requirement: Rerun chain navigation

The JobDetail page SHALL display the current run number and provide navigation links to previous and next runs in the rerun chain.

#### Scenario: First run with no reruns

- **WHEN** user views a job that has no parent and no children
- **THEN** no chain navigation is displayed

#### Scenario: Rerun job shows run number and parent link

- **WHEN** user views a rerun job (has `parent_job_id`)
- **THEN** the page displays the run number (e.g., "Run #2") and a link to the previous run

#### Scenario: Parent job with child shows next link

- **WHEN** user views a job that has been rerun (another job references it as parent)
- **THEN** the page displays a link to the next run

### Requirement: Rerun API client function

The frontend API client (`api.js`) SHALL include a `rerunJob(jobId)` function that calls `POST /api/v1/jobs/{id}/rerun` and returns the new job response.

#### Scenario: API client rerun call

- **WHEN** `rerunJob(jobId)` is called
- **THEN** it sends an authenticated POST request to `/api/v1/jobs/{jobId}/rerun` and returns the parsed response

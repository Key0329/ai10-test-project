## ADDED Requirements

### Requirement: Credential storage strategy

The `useCredentials` composable SHALL store Jira email in `localStorage` for persistence across browser sessions. GitHub token and Jira API token SHALL remain in `sessionStorage` and be cleared when the browser tab is closed.

#### Scenario: Jira email persists after tab close

- **WHEN** a user enters a Jira email on the Dashboard and closes the browser tab
- **THEN** the Jira email SHALL be available in the input field when the user reopens the page

#### Scenario: Tokens cleared after tab close

- **WHEN** a user enters a GitHub token or Jira API token and closes the browser tab
- **THEN** the GitHub token and Jira API token fields SHALL be empty when the user reopens the page

#### Scenario: Credential save writes to correct storage

- **WHEN** the `save()` function is called
- **THEN** `jira_email` SHALL be written to `localStorage` and `github_token` and `jira_api_token` SHALL be written to `sessionStorage`

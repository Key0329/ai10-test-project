"""Job data models."""

from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional
from datetime import datetime
import re


class JobCreate(BaseModel):
    repo_url: str = Field(..., description="Git repo URL")
    jira_ticket: str = Field(..., description="Jira ticket ID, e.g. JRA-123")
    branch: Optional[str] = Field(None, description="Branch to clone")
    extra_prompt: Optional[str] = Field(None, max_length=2000)
    priority: int = Field(3, ge=1, le=5)
    requested_by: Optional[str] = Field(None, max_length=100)
    agent_mode: Literal["claude_code", "copilot"] = Field("claude_code", description="Execution engine")
    # MCP 設定（僅 copilot 模式使用，不寫入 DB）
    selected_mcps: list[str] = Field(default_factory=lambda: ["context7"], description="選擇的 MCP server ID 清單")
    mcp_tokens: dict[str, str] = Field(default_factory=dict, description="各 MCP 的 token")
    # 憑證欄位：只用於本次執行，不寫入 DB
    github_token: str = Field(..., description="GitHub Personal Access Token")
    jira_api_token: str = Field(..., description="Jira API Token")
    jira_email: str = Field(..., description="Jira account email")

    @field_validator("jira_ticket")
    @classmethod
    def validate_jira_ticket(cls, v: str) -> str:
        if not re.match(r"^[A-Z]{1,10}-\d{1,6}$", v.upper()):
            raise ValueError("Invalid Jira ticket format. Expected: ABC-123")
        return v.upper()

    @field_validator("repo_url")
    @classmethod
    def validate_repo_url(cls, v: str) -> str:
        if not v.startswith("https://"):
            raise ValueError("Only HTTPS repo URLs are allowed")
        if not re.match(r"^https://[\w.\-]+/[\w.\-/]+(?:\.git)?$", v):
            raise ValueError("Invalid repo URL format")
        return v

    @field_validator("branch")
    @classmethod
    def validate_branch(cls, v: Optional[str]) -> Optional[str]:
        if v and not re.match(r"^[a-zA-Z0-9._/\-]+$", v):
            raise ValueError("Invalid branch name")
        return v


class JobResponse(BaseModel):
    job_id: str
    repo_url: str
    jira_ticket: str
    branch: Optional[str]
    extra_prompt: Optional[str]
    priority: int
    requested_by: Optional[str]
    agent_mode: str = "claude_code"
    status: str
    exit_code: Optional[int]
    pr_url: Optional[str]
    error_message: Optional[str]
    created_at: str
    started_at: Optional[str]
    finished_at: Optional[str]
    parent_job_id: Optional[str] = None
    position: Optional[int] = None


class JobListResponse(BaseModel):
    jobs: list[JobResponse]
    total: int
    running: int
    queued: int


class RerunRequest(BaseModel):
    """Rerun 時傳入的憑證，不寫入 DB。"""
    github_token: str
    jira_api_token: str
    jira_email: str


class CallbackPayload(BaseModel):
    job_id: str
    jira_ticket: str
    status: str = Field(..., pattern="^(done|failed)$")
    pr_url: Optional[str] = None
    summary: Optional[str] = None
    error: Optional[str] = None

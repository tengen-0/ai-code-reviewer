"""AI-assisted code review API with deterministic guardrails.

The heuristic engine is always available and safe to run in CI. An optional
OpenAI-compatible provider can enrich the review when REVIEW_PROVIDER=openai.
"""
from __future__ import annotations

import json
import os
import re
from typing import List, Literal, Protocol

import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, HttpUrl


Severity = Literal["critical", "high", "medium", "low", "info"]


class PullRequestPayload(BaseModel):
    repo_url: HttpUrl = Field(..., description="URL of the GitHub repository")
    pr_number: int = Field(..., ge=1, description="Pull request number")
    author: str = Field(..., min_length=1, max_length=120)
    diff: str = Field("", max_length=250_000, description="Unified diff to review")


class Finding(BaseModel):
    rule_id: str
    severity: Severity
    message: str
    file: str | None = None
    line: int | None = Field(default=None, ge=1)
    suggestion: str | None = None


class ReviewResult(BaseModel):
    status: Literal["completed", "failed"]
    comments_count: int
    summary: str
    security_issues_found: List[str]
    findings: List[Finding]
    provider: str


class ReviewProvider(Protocol):
    name: str

    def review(self, diff: str) -> list[Finding]: ...


SECRET_PATTERNS = (
    ("secret-api-key", re.compile(r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*['\"][^'\"]{12,}['\"]")),
    ("private-key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("database-password", re.compile(r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"][^'\"]+['\"]")),
)
DANGEROUS_PATTERNS = (
    ("python-eval", re.compile(r"\beval\s*\("), "Use a safe parser or an explicit allow-list instead of eval()."),
    ("python-exec", re.compile(r"\bexec\s*\("), "Avoid exec(); validate and model inputs explicitly."),
    ("shell-injection", re.compile(r"\b(os\.system|subprocess\.(run|Popen|call))\s*\("), "Pass an argument list and keep shell=False; validate user input."),
    ("sql-concat", re.compile(r"(?i)(select|insert|update|delete).*(\+|f['\"]|format\()"), "Use parameterized queries rather than string interpolation."),
)


def _diff_lines(diff: str):
    current_file: str | None = None
    new_line = 0
    for raw in diff.splitlines():
        if raw.startswith("+++ b/"):
            current_file = raw[6:]
        elif raw.startswith("@@"):
            match = re.search(r"\+([0-9]+)", raw)
            new_line = int(match.group(1)) if match else 0
        elif raw.startswith("+") and not raw.startswith("+++"):
            new_line += 1
            yield current_file, new_line, raw[1:]
        elif not raw.startswith("-"):
            new_line += 1


class HeuristicProvider:
    name = "heuristic"

    def review(self, diff: str) -> list[Finding]:
        findings: list[Finding] = []
        for filename, line, content in _diff_lines(diff):
            for rule_id, pattern in SECRET_PATTERNS:
                if pattern.search(content):
                    findings.append(Finding(
                        rule_id=rule_id, severity="critical", message="Potential hard-coded credential detected.",
                        file=filename, line=line, suggestion="Move the value to a secret manager or environment variable.",
                    ))
            for rule_id, pattern, suggestion in DANGEROUS_PATTERNS:
                if pattern.search(content):
                    findings.append(Finding(
                        rule_id=rule_id, severity="high", message=f"Potentially unsafe operation: {rule_id}.",
                        file=filename, line=line, suggestion=suggestion,
                    ))
        return findings


class OpenAIProvider:
    name = "openai"

    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.base_url = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1").rstrip("/")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def review(self, diff: str) -> list[Finding]:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is required when REVIEW_PROVIDER=openai")
        prompt = (
            "Review this unified diff. Return ONLY a JSON array of objects with keys "
            "rule_id, severity (critical/high/medium/low/info), message, file, line, suggestion. "
            "Report concrete correctness, security, and maintainability issues; do not invent issues.\n\n"
            f"{diff}"
        )
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={"model": self.model, "temperature": 0, "messages": [{"role": "user", "content": prompt}]},
            timeout=30,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        payload = json.loads(content[content.find("["):content.rfind("]") + 1])
        return [Finding.model_validate(item) for item in payload]


def get_provider() -> ReviewProvider:
    return OpenAIProvider() if os.getenv("REVIEW_PROVIDER", "heuristic").lower() == "openai" else HeuristicProvider()


app = FastAPI(title="AI-Powered Code Reviewer", description="Structured, CI-friendly code review API.", version="2.0.0")


@app.get("/", tags=["health"])
def read_root():
    return {"service": "ai-code-reviewer", "status": "ok", "version": app.version}


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "provider": get_provider().name}


@app.post("/review", response_model=ReviewResult, tags=["review"])
def review_pull_request(payload: PullRequestPayload) -> ReviewResult:
    provider = get_provider()
    try:
        findings = provider.review(payload.diff)
    except (requests.RequestException, RuntimeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=502, detail=f"Review provider failed: {exc}") from exc

    security = [f.message for f in findings if f.severity in {"critical", "high"}]
    status = "completed"
    summary = (
        f"Reviewed PR #{payload.pr_number} by {payload.author}: "
        f"{len(findings)} finding(s) from {provider.name} analysis."
    )
    return ReviewResult(
        status=status,
        comments_count=len(findings),
        summary=summary,
        security_issues_found=security,
        findings=findings,
        provider=provider.name,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")))

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class RepositoryCandidate:
    full_name: str
    html_url: str
    description: str | None
    default_branch: str
    pushed_at: str | None
    archived: bool
    stars: int
    forks: int
    discovery_query: str

    @classmethod
    def from_api(cls, raw: dict[str, Any], query: str) -> "RepositoryCandidate":
        full_name = raw.get("full_name")
        html_url = raw.get("html_url")
        default_branch = raw.get("default_branch")
        if not all(isinstance(x, str) and x for x in (full_name, html_url, default_branch)):
            raise ValueError("GitHub repository response is missing required identity fields")
        return cls(
            full_name=full_name,
            html_url=html_url,
            description=raw.get("description"),
            default_branch=default_branch,
            pushed_at=raw.get("pushed_at"),
            archived=bool(raw.get("archived", False)),
            stars=int(raw.get("stargazers_count", 0)),
            forks=int(raw.get("forks_count", 0)),
            discovery_query=query,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvidenceRecord:
    repository: str
    commit_sha: str
    path: str
    blob_sha: str
    claim_type: str
    claim: str
    evidence_excerpt: str
    confidence: str = "medium"
    acceptance_status: str = "pending"

    def validate(self) -> None:
        if len(self.commit_sha) != 40 or any(c not in "0123456789abcdef" for c in self.commit_sha.lower()):
            raise ValueError("commit_sha must be a full 40-character hexadecimal SHA")
        if len(self.blob_sha) != 40 or any(c not in "0123456789abcdef" for c in self.blob_sha.lower()):
            raise ValueError("blob_sha must be a full 40-character hexadecimal SHA")
        if self.claim_type not in {"observed_fact", "inference", "hypothesis", "unknown"}:
            raise ValueError("unsupported claim_type")
        if self.acceptance_status not in {"pending", "accepted", "rejected", "needs_human_review"}:
            raise ValueError("unsupported acceptance_status")
        if self.confidence not in {"low", "medium", "high"}:
            raise ValueError("unsupported confidence")
        if not self.repository or self.repository.count("/") != 1 or not self.path or not self.claim.strip():
            raise ValueError("repository must be owner/name; path and claim are required")

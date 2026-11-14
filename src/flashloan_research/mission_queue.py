from __future__ import annotations

import json
import re
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DOMAINS = {
    "flash_loan_arbitrage", "defi_liquidation", "protocol_security",
    "mev_and_execution", "cross_protocol_research", "general_defi_research",
}
DEPTHS = {"screening", "standard", "deep_forensic", "full_audit"}
MODES = {"autonomous", "approval_gated", "supervised"}
AGENTS = {
    "research_director", "github_discovery", "protocol_specialist",
    "solidity_security", "execution_engineer", "test_verification",
    "economics_quant", "dependency_license", "evidence_auditor",
    "independent_reviewer", "continuity_documentation",
}
DELIVERABLES = {
    "candidate_matrix", "protocol_architecture", "source_audits",
    "security_findings", "test_and_ci_evidence", "profitability_model",
    "dependency_license_report", "evidence_register", "executive_summary",
    "next_research_queue",
}
MISSION_DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS research_missions (
 mission_id TEXT PRIMARY KEY,
 title TEXT NOT NULL,
 status TEXT NOT NULL,
 payload_json TEXT NOT NULL,
 created_at_utc TEXT NOT NULL,
 updated_at_utc TEXT NOT NULL,
 rejection_reason TEXT
);
CREATE INDEX IF NOT EXISTS idx_research_missions_status_created
 ON research_missions(status, created_at_utc);
"""


class MissionValidationError(ValueError):
    pass


def validate_mission(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise MissionValidationError("mission payload must be a JSON object")
    allowed = {"mission_id", "title", "objective", "domain", "scope",
               "research_depth", "agent_policy", "safety_policy", "deliverables",
               "acceptance_criteria", "created_at_utc"}
    unknown = sorted(payload.keys() - allowed)
    if unknown:
        raise MissionValidationError(f"unknown mission fields: {', '.join(unknown)}")
    required = {"mission_id", "title", "objective", "domain", "scope",
                "research_depth", "agent_policy", "safety_policy", "deliverables"}
    missing = sorted(required - payload.keys())
    if missing:
        raise MissionValidationError(f"missing required fields: {', '.join(missing)}")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,63}", str(payload["mission_id"])):
        raise MissionValidationError("mission_id must be 3-64 lowercase letters, digits or hyphens")
    if not isinstance(payload["title"], str) or not 5 <= len(payload["title"].strip()) <= 160:
        raise MissionValidationError("title must contain 5-160 characters")
    if not isinstance(payload["objective"], str) or not 20 <= len(payload["objective"].strip()) <= 5000:
        raise MissionValidationError("objective must contain 20-5000 characters")
    if payload["domain"] not in DOMAINS:
        raise MissionValidationError("unsupported research domain")
    if payload["research_depth"] not in DEPTHS:
        raise MissionValidationError("unsupported research depth")

    scope = payload["scope"]
    if not isinstance(scope, dict):
        raise MissionValidationError("scope must be an object")
    chains, protocols = scope.get("chains", []), scope.get("protocols", [])
    if not isinstance(chains, list) or not all(isinstance(x, str) and 0 < len(x) <= 80 for x in chains):
        raise MissionValidationError("scope.chains must be an array of non-empty strings")
    if not isinstance(protocols, list) or not all(isinstance(x, str) and 0 < len(x) <= 120 for x in protocols):
        raise MissionValidationError("scope.protocols must be an array of non-empty strings")
    allowed_scope = {"chains", "protocols", "repository_limit", "include_archived",
                     "include_older_references", "date_cutoff", "keyword_taxonomy_version",
                     "discovery_query_families", "search_per_page", "max_pages_per_query",
                     "include_forked"}
    if set(scope) - allowed_scope:
        raise MissionValidationError("scope contains unknown fields")
    for flag in ("include_archived", "include_older_references"):
        if flag in scope and not isinstance(scope[flag], bool):
            raise MissionValidationError(f"scope.{flag} must be boolean")
    limit = scope.get("repository_limit", 100)
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 500:
        raise MissionValidationError("repository_limit must be an integer from 1 to 500")
    family_ids = {
        "flash_loan_core", "flash_loan_provider_apis", "defi_liquidation",
        "flash_loan_liquidation_combo", "arbitrage", "mev_execution",
        "lending_protocols", "dex_and_liquidity", "security_accounting",
        "cross_chain_infrastructure", "tooling_and_research",
    }
    families = scope.get("discovery_query_families", [])
    if not isinstance(families, list) or len(families) != len(set(families)) or any(x not in family_ids for x in families):
        raise MissionValidationError("discovery_query_families must contain unique supported taxonomy IDs")
    taxonomy_version = scope.get("keyword_taxonomy_version", "1.0.0")
    if not isinstance(taxonomy_version, str) or not 1 <= len(taxonomy_version) <= 20:
        raise MissionValidationError("keyword_taxonomy_version must be a non-empty string up to 20 characters")
    per_page = scope.get("search_per_page", 100)
    max_pages = scope.get("max_pages_per_query", 10)
    if isinstance(per_page, bool) or not isinstance(per_page, int) or not 1 <= per_page <= 100:
        raise MissionValidationError("search_per_page must be an integer from 1 to 100")
    if isinstance(max_pages, bool) or not isinstance(max_pages, int) or not 1 <= max_pages <= 10:
        raise MissionValidationError("max_pages_per_query must be an integer from 1 to 10")
    if "include_forked" in scope and not isinstance(scope["include_forked"], bool):
        raise MissionValidationError("scope.include_forked must be boolean")

    policy = payload["agent_policy"]
    if not isinstance(policy, dict) or set(policy) - {"mode", "independent_review", "max_parallel_agents", "max_iterations", "specialists"}:
        raise MissionValidationError("agent_policy must be an object with supported fields only")
    if policy.get("mode") not in MODES:
        raise MissionValidationError("agent_policy.mode is invalid")
    if policy.get("independent_review") is not True:
        raise MissionValidationError("independent review is mandatory")
    parallel = policy.get("max_parallel_agents", 5)
    iterations = policy.get("max_iterations", 5)
    if isinstance(parallel, bool) or not isinstance(parallel, int) or not 1 <= parallel <= 12:
        raise MissionValidationError("max_parallel_agents must be 1-12")
    if isinstance(iterations, bool) or not isinstance(iterations, int) or not 1 <= iterations <= 20:
        raise MissionValidationError("max_iterations must be 1-20")
    specialists = policy.get("specialists", [])
    if not isinstance(specialists, list) or any(x not in AGENTS for x in specialists):
        raise MissionValidationError("agent_policy.specialists contains an unknown role")
    if "independent_reviewer" not in specialists:
        raise MissionValidationError("independent_reviewer must be included")

    safety = payload["safety_policy"]
    allowed_safety = {"research_only", "execute_candidate_code", "wallet_access",
                      "sign_transactions", "deploy_contracts", "live_trading",
                      "paid_services", "allow_free_model_inference"}
    if not isinstance(safety, dict) or set(safety) - allowed_safety:
        raise MissionValidationError("safety_policy contains unknown fields")
    locked_false = ("execute_candidate_code", "wallet_access", "sign_transactions",
                    "deploy_contracts", "live_trading", "paid_services")
    if not isinstance(safety, dict) or safety.get("research_only") is not True:
        raise MissionValidationError("research_only must be true")
    for key in locked_false:
        if safety.get(key) is not False:
            raise MissionValidationError(f"safety policy violation: {key} must remain false")

    deliverables = payload["deliverables"]
    if not isinstance(deliverables, list) or not deliverables:
        raise MissionValidationError("at least one deliverable is required")
    if any(x not in DELIVERABLES for x in deliverables):
        raise MissionValidationError("deliverables contains an unsupported value")

    if "acceptance_criteria" in payload:
        criteria = payload["acceptance_criteria"]
        if not isinstance(criteria, list) or any(not isinstance(x, str) or len(x) > 500 for x in criteria):
            raise MissionValidationError("acceptance_criteria must be an array of strings up to 500 characters")
    return payload


class MissionQueue:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.db_path, timeout=10, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA busy_timeout=10000")
        self.connection.executescript(MISSION_DB_SCHEMA)
        self.connection.commit()

    def close(self) -> None:
        with self._lock:
            self.connection.close()

    def enqueue(self, payload: Any) -> dict[str, Any]:
        mission = validate_mission(payload)
        now = datetime.now(timezone.utc).isoformat()
        encoded = json.dumps(mission, ensure_ascii=False, sort_keys=True)
        try:
            with self._lock:
                self.connection.execute(
                    "INSERT INTO research_missions(mission_id,title,status,payload_json,created_at_utc,updated_at_utc) VALUES(?,?,?,?,?,?)",
                    (mission["mission_id"], mission["title"], "queued", encoded, now, now),
                )
                self.connection.commit()
        except sqlite3.IntegrityError as exc:
            raise MissionValidationError("mission_id already exists; use a new mission_id") from exc
        return {"mission_id": mission["mission_id"], "status": "queued", "created_at_utc": now}

    def get(self, mission_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self.connection.execute(
                "SELECT mission_id,title,status,payload_json,created_at_utc,updated_at_utc,rejection_reason FROM research_missions WHERE mission_id=?",
                (mission_id,),
            ).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["payload"] = json.loads(result.pop("payload_json"))
        return result

    def list_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            rows = self.connection.execute(
                "SELECT mission_id,title,status,created_at_utc,updated_at_utc FROM research_missions ORDER BY created_at_utc DESC LIMIT ?",
                (min(max(limit, 1), 100),),
            ).fetchall()
        return [dict(row) for row in rows]

from __future__ import annotations

import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import RepositoryCandidate


class DiscoveryPlanError(ValueError):
    pass


def load_taxonomy(path: Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("families"), list):
        raise DiscoveryPlanError("taxonomy must contain a families array")
    if not isinstance(data.get("family_queries"), dict):
        raise DiscoveryPlanError("taxonomy must contain family_queries mapping")
    family_ids = {item.get("id") for item in data["families"] if isinstance(item, dict)}
    if not family_ids or set(data["family_queries"]) - family_ids:
        raise DiscoveryPlanError("family_queries contains unknown or no family identifiers")
    for family_id, queries in data["family_queries"].items():
        if not isinstance(queries, list) or not queries or any(not isinstance(q, str) or not q.strip() for q in queries):
            raise DiscoveryPlanError(f"taxonomy family {family_id} must have non-empty query strings")
    return data


def run_taxonomy_discovery(
    client: Any,
    store: Any,
    taxonomy_path: Path,
    selected_families: list[str] | None = None,
    per_page: int = 100,
    max_pages: int = 10,
    include_archived: bool = False,
    include_forked: bool = True,
) -> dict[str, Any]:
    """Run bounded, paginated public repository searches and persist a coverage manifest.

    The runner never treats search results as proof of implementation. Repository
    candidates are deduplicated by stable GitHub ID when available, then canonical
    full name. Query/page failures remain explicit coverage debt.
    """
    if not 1 <= per_page <= 100:
        raise ValueError("per_page must be between 1 and 100")
    if not 1 <= max_pages <= 10:
        raise ValueError("max_pages must be between 1 and 10")

    taxonomy = load_taxonomy(taxonomy_path)
    available = set(taxonomy["family_queries"])
    families = selected_families if selected_families is not None else sorted(available)
    unknown = sorted(set(families) - available)
    if unknown:
        raise DiscoveryPlanError(f"unknown discovery families: {', '.join(unknown)}")
    if not families:
        raise DiscoveryPlanError("at least one discovery family must be selected")

    family_labels = {
        item["id"]: item.get("label", item["id"])
        for item in taxonomy["families"]
        if isinstance(item, dict) and item.get("id") in available
    }
    candidates: dict[str, dict[str, Any]] = {}
    identity_to_name: dict[str, str] = {}
    query_coverage: list[dict[str, Any]] = []
    started = datetime.now(timezone.utc).isoformat()

    for family_id in families:
        for query in taxonomy["family_queries"][family_id]:
            query_record: dict[str, Any] = {
                "family_id": family_id,
                "family_label": family_labels.get(family_id, family_id),
                "query": query,
                "per_page": per_page,
                "max_pages": max_pages,
                "pages": [],
                "total_count": None,
                "incomplete_results": None,
                "search_cap_hit": False,
                "page_limit_hit": False,
                "status": "running",
                "error": None,
            }
            for page in range(1, max_pages + 1):
                try:
                    response = client.get(
                        "/search/repositories",
                        {"q": query, "per_page": str(per_page), "page": str(page)},
                    )
                    if not isinstance(response, dict) or not isinstance(response.get("items"), list):
                        raise DiscoveryPlanError("GitHub search response missing items array")
                    total_count = response.get("total_count")
                    if isinstance(total_count, bool) or not isinstance(total_count, int) or total_count < 0:
                        raise DiscoveryPlanError("GitHub search response missing valid total_count")
                    incomplete = response.get("incomplete_results", False)
                    if not isinstance(incomplete, bool):
                        incomplete = True
                    query_record["total_count"] = total_count
                    query_record["incomplete_results"] = incomplete
                    query_record["search_cap_hit"] = total_count > 1000
                    items = response["items"]
                    page_record = {
                        "page": page,
                        "returned_count": len(items),
                        "incomplete_results": incomplete,
                        "repository_search_cap": total_count > 1000,
                    }
                    query_record["pages"].append(page_record)
                    for raw in items:
                        if not isinstance(raw, dict):
                            continue
                        full_name = raw.get("full_name")
                        if not isinstance(full_name, str) or full_name.count("/") != 1:
                            continue
                        if raw.get("archived") and not include_archived:
                            continue
                        if raw.get("fork") and not include_forked:
                            continue
                        stable_id = raw.get("id")
                        identity = f"id:{stable_id}" if isinstance(stable_id, int) and not isinstance(stable_id, bool) else f"name:{full_name.lower()}"
                        existing_name = identity_to_name.get(identity)
                        canonical_name = existing_name or full_name
                        if canonical_name not in candidates:
                            candidate = RepositoryCandidate.from_api(raw, f"{family_id}:{query}")
                            candidates[canonical_name] = {
                                "candidate": candidate,
                                "repository_id": stable_id if isinstance(stable_id, int) else None,
                                "discovered_by": [],
                            }
                            identity_to_name[identity] = canonical_name
                        match = {"family_id": family_id, "query": query, "page": page}
                        if match not in candidates[canonical_name]["discovered_by"]:
                            candidates[canonical_name]["discovered_by"].append(match)
                    if len(items) < per_page:
                        break
                    if page == max_pages:
                        expected_pages = min(10, math.ceil(min(total_count, 1000) / per_page))
                        query_record["page_limit_hit"] = page < expected_pages
                except Exception as exc:
                    query_record["status"] = "incomplete"
                    query_record["error"] = f"{type(exc).__name__}: {str(exc)[:500]}"
                    break
            if query_record["status"] == "running":
                if query_record["incomplete_results"]:
                    query_record["status"] = "incomplete"
                elif query_record["search_cap_hit"]:
                    query_record["status"] = "capped"
                elif query_record["page_limit_hit"]:
                    query_record["status"] = "incomplete"
                else:
                    query_record["status"] = "complete"
            query_coverage.append(query_record)

    for full_name, row in candidates.items():
        candidate = row["candidate"]
        queries = sorted({hit["query"] for hit in row["discovered_by"]})
        families_for_candidate = sorted({hit["family_id"] for hit in row["discovered_by"]})
        candidate = RepositoryCandidate(
            full_name=candidate.full_name,
            html_url=candidate.html_url,
            description=candidate.description,
            default_branch=candidate.default_branch,
            pushed_at=candidate.pushed_at,
            archived=candidate.archived,
            stars=candidate.stars,
            forks=candidate.forks,
            discovery_query="; ".join(families_for_candidate) + " | " + " || ".join(queries[:8]),
        )
        store.upsert_candidate(candidate)
        row["candidate"] = candidate.to_dict()
        row["matched_families"] = families_for_candidate

    incomplete_queries = [q for q in query_coverage if q["status"] != "complete"]
    return {
        "schema_version": "1.0",
        "record_type": "flashloan_mission_discovery_coverage",
        "taxonomy_version": taxonomy.get("taxonomy_version", "unknown"),
        "started_at_utc": started,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "parameters": {
            "selected_families": families,
            "per_page": per_page,
            "max_pages_per_query": max_pages,
            "include_archived": include_archived,
            "include_forked": include_forked,
        },
        "query_count": len(query_coverage),
        "complete_query_count": sum(1 for q in query_coverage if q["status"] == "complete"),
        "incomplete_query_count": len(incomplete_queries),
        "coverage_complete": not incomplete_queries,
        "coverage_debt": [
            {"family_id": q["family_id"], "query": q["query"], "status": q["status"],
             "total_count": q["total_count"], "pages_captured": len(q["pages"]), "error": q["error"],
             "search_cap_hit": q["search_cap_hit"], "page_limit_hit": q["page_limit_hit"]}
            for q in incomplete_queries
        ],
        "unique_candidate_count": len(candidates),
        "candidates": [
            {"repository": name, "repository_id": row["repository_id"],
             "metadata": row["candidate"], "discovered_by": row["discovered_by"],
             "matched_families": row["matched_families"]}
            for name, row in sorted(candidates.items())
        ],
        "query_coverage": query_coverage,
        "limitations": [
            "GitHub repository search covers indexed name, description and README matches; it is not a complete index of source-code contents.",
            "Search ranking and API indexing can omit relevant public repositories.",
            "Each query is bounded by GitHub's 1,000-result search ceiling and the mission's max_pages_per_query.",
            "A repository discovery hit is a candidate only; purpose and implementation require commit-pinned source inspection.",
            "No candidate repository code was executed.",
        ],
    }

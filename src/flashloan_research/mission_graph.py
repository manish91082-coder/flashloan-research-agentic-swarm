from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict

from .config import SETTINGS
from .mission_executor import MissionExecutor


class MissionGraphState(TypedDict, total=False):
    mission_id: str
    prepare: dict[str, Any]
    discovery: dict[str, Any]
    candidate_expansion: dict[str, Any]
    source_inspection: dict[str, Any]
    semantic_agents: dict[str, Any]
    final: dict[str, Any]


def build_mission_graph(executor: MissionExecutor, checkpointer: Any = None):
    """Compile the checkpointed control-flow graph for a research mission."""
    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError as exc:
        raise RuntimeError(
            "LangGraph runtime is optional. Install with: pip install -e '.[agentic]'"
        ) from exc

    builder = StateGraph(MissionGraphState)

    def prepare_node(state: MissionGraphState) -> dict[str, Any]:
        return {"prepare": executor.prepare(state["mission_id"])}

    def discovery_node(state: MissionGraphState) -> dict[str, Any]:
        return {"discovery": executor.discover(state["mission_id"])}

    def expansion_node(state: MissionGraphState) -> dict[str, Any]:
        return {"candidate_expansion": executor.merge_and_expand(state["mission_id"])}

    def inspection_node(state: MissionGraphState) -> dict[str, Any]:
        return {"source_inspection": executor.inspect_candidate_batch(state["mission_id"])}

    def semantic_node(state: MissionGraphState) -> dict[str, Any]:
        return {"semantic_agents": executor.run_local_semantic_agents(state["mission_id"])}

    def finalize_node(state: MissionGraphState) -> dict[str, Any]:
        return {"final": executor.finalize(state["mission_id"])}

    builder.add_node("research_director", prepare_node)
    builder.add_node("github_discovery_swarm", discovery_node)
    builder.add_node("candidate_triage_and_task_expansion", expansion_node)
    builder.add_node("commit_pinned_source_inspection", inspection_node)
    builder.add_node("semantic_specialists_evidence_gate_and_review", semantic_node)
    builder.add_node("mission_checkpoint_and_handoff", finalize_node)

    builder.add_edge(START, "research_director")
    builder.add_edge("research_director", "github_discovery_swarm")
    builder.add_edge("github_discovery_swarm", "candidate_triage_and_task_expansion")
    builder.add_edge("candidate_triage_and_task_expansion", "commit_pinned_source_inspection")
    builder.add_edge("commit_pinned_source_inspection", "semantic_specialists_evidence_gate_and_review")
    builder.add_edge("semantic_specialists_evidence_gate_and_review", "mission_checkpoint_and_handoff")
    builder.add_edge("mission_checkpoint_and_handoff", END)
    return builder.compile(checkpointer=checkpointer)


def run_mission_graph(
    mission_id: str,
    database_path: Path | None = None,
    taxonomy_path: Path = Path("research/keyword-taxonomy.json"),
    artifact_root: Path = Path("research_runs/mission"),
    checkpoint_path: Path | None = None,
) -> dict[str, Any]:
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver
    except ImportError as exc:
        raise RuntimeError(
            "SQLite checkpoint support is optional. Install with: pip install -e '.[agentic]'"
        ) from exc

    db_path = Path(database_path or SETTINGS.database_path)
    checkpoint_db = Path(checkpoint_path or db_path.with_name("langgraph-checkpoints.sqlite3"))
    checkpoint_db.parent.mkdir(parents=True, exist_ok=True)
    executor = MissionExecutor(db_path, Path(taxonomy_path), Path(artifact_root))
    with SqliteSaver.from_conn_string(str(checkpoint_db)) as checkpointer:
        graph = build_mission_graph(executor, checkpointer)
        config = {"configurable": {"thread_id": mission_id}}
        result = graph.invoke({"mission_id": mission_id}, config=config)
    return result

"""EquiClaim `StateGraph` assembly — Orchestrator-Worker-Evaluator topology.

```
START -> intake_forensic_worker -> mrf_benchmark_worker -> nsa_compliance_worker
      -> actuarial_evaluator_node --(CERTIFIED)--> finalize_docket --> END
                                  --(any defect)--> manual_escalation --> END
```

There is no separate top-level "Orchestrator" node: `START` sequences the
three workers directly (the orchestration *is* the static graph topology).
A defect does not return to a worker: those workers recompute the same
documents, so the evaluator stops at `manual_escalation`. `finalize_docket` is the
sole `interrupt_before` target for the Human-in-the-Loop breakpoint.

`intake_forensic_worker` and `nsa_compliance_worker` are pure functions of
state (no external dependencies) and are added directly. `mrf_benchmark_worker`
and `actuarial_evaluator_node` need a Postgres pool / the iteration cap
respectively, so they are built via factory functions and closed over their
dependencies at graph-construction time — this is the project's dependency-
injection seam for LangGraph nodes (see each factory's own docstring).
"""

from __future__ import annotations

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy
from psycopg import InterfaceError, OperationalError
from psycopg_pool import AsyncConnectionPool

from app.core.config import Settings
from app.graph.nodes.evaluator import build_evaluator_node, route_after_evaluator
from app.graph.nodes.finalize import finalize_docket, manual_escalation
from app.graph.nodes.intake import intake_forensic_worker
from app.graph.nodes.mrf_benchmark import build_mrf_benchmark_worker
from app.graph.nodes.nsa_compliance import nsa_compliance_worker
from app.graph.state import EquiClaimState

NODE_INTAKE = "intake_forensic_worker"
NODE_MRF_BENCHMARK = "mrf_benchmark_worker"
NODE_NSA_COMPLIANCE = "nsa_compliance_worker"
NODE_EVALUATOR = "actuarial_evaluator_node"
NODE_FINALIZE = "finalize_docket"
NODE_ESCALATE = "manual_escalation"

# The benchmark node is the only worker that talks to Postgres. Retry a dropped
# connection; do not retry validation or programming errors.
_MRF_RETRY = RetryPolicy(
    initial_interval=0.2,
    max_attempts=3,
    retry_on=lambda exc: isinstance(exc, (OperationalError, InterfaceError)),
)


def build_graph(*, pool: AsyncConnectionPool, settings: Settings) -> StateGraph:
    """Construct (but do not compile) the EquiClaim `StateGraph`."""
    graph = StateGraph(EquiClaimState)

    graph.add_node(NODE_INTAKE, intake_forensic_worker)
    graph.add_node(NODE_MRF_BENCHMARK, build_mrf_benchmark_worker(pool), retry_policy=_MRF_RETRY)
    graph.add_node(NODE_NSA_COMPLIANCE, nsa_compliance_worker)
    graph.add_node(
        NODE_EVALUATOR, build_evaluator_node(max_iterations=settings.evaluator_max_iterations)
    )
    graph.add_node(NODE_FINALIZE, finalize_docket)
    graph.add_node(NODE_ESCALATE, manual_escalation)

    graph.add_edge(START, NODE_INTAKE)
    graph.add_edge(NODE_INTAKE, NODE_MRF_BENCHMARK)
    graph.add_edge(NODE_MRF_BENCHMARK, NODE_NSA_COMPLIANCE)
    graph.add_edge(NODE_NSA_COMPLIANCE, NODE_EVALUATOR)

    graph.add_conditional_edges(
        NODE_EVALUATOR,
        route_after_evaluator,
        {
            NODE_MRF_BENCHMARK: NODE_MRF_BENCHMARK,
            NODE_NSA_COMPLIANCE: NODE_NSA_COMPLIANCE,
            NODE_FINALIZE: NODE_FINALIZE,
            NODE_ESCALATE: NODE_ESCALATE,
        },
    )

    graph.add_edge(NODE_FINALIZE, END)
    graph.add_edge(NODE_ESCALATE, END)

    return graph


def compile_graph(
    *, pool: AsyncConnectionPool, checkpointer: BaseCheckpointSaver, settings: Settings
):
    """Build and compile the graph with the HITL interrupt wired on `finalize_docket`."""
    return build_graph(pool=pool, settings=settings).compile(
        checkpointer=checkpointer,
        interrupt_before=[NODE_FINALIZE],
    )

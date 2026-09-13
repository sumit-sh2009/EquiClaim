# EquiClaim architecture

Technical note for engineers and faculty. Every section is scoped to what can be opened in this repository. Claims that cannot be traced to a file are labeled `[NOT VERIFIED IN CODE — confirm before publishing]`.

**Audit commit:** `b772ac63fdff714449060902538f1088df308f58` (`Initial commit` on `main`, 2026-09-13).  
**Remote:** `https://github.com/sumit-sh2009/EquiClaim`  
**Local tree walked:** `/workspace` excluding `.git/`.  
**Also checked:** GitHub contents API for `sumit-sh2009/EquiClaim` at the same SHA (only `LICENSE` on `main` before this documentation branch).

This is not a design-fiction document. It is an inventory.

---

## 1. What "architecture" can mean here

In a running EquiClaim tree, this file would describe AgentState channels, LangGraph nodes and edges, actuarial invariants, PostgreSQL indexes, `AsyncPostgresSaver` checkpointing, HTTP routes, and ingestion of MRF / PFS / NCCI / CARC/RARC **only as those objects appear in source**.

In *this* tree, the architecture is:

1. A single legal artifact ([`LICENSE`](../LICENSE)).
2. Four documentation files that refuse to invent a runtime.

There is no process graph, no persistence layer, and no API surface. The diagrams in [`state_diagram.md`](state_diagram.md) and [`sequence_diagram.md`](sequence_diagram.md) are drawn from that fact, not from a generic multi-agent template.

---

## 2. Verification method

Before writing, the following were searched on the local clone and on GitHub `main`:

| Probe | Result |
| --- | --- |
| `git ls-tree -r HEAD` | `LICENSE` only (pre-docs). |
| Filenames `models.py`, `schemas.py`, `types.ts` | Absent. |
| LangGraph symbols (`StateGraph`, `add_node`, `add_edge`, `AgentState`, `AsyncPostgresSaver`) | Absent. |
| Route decorators / routers (`@app.`, `APIRouter`, `express()`, `app.get`, `app.post`) | Absent. |
| Dependency manifests (`requirements.txt`, `pyproject.toml`, `package.json`, `Pipfile`, `Cargo.toml`, `go.mod`) | Absent. |
| Env templates (`.env.example`, `.env.sample`) | Absent. |
| Migration / schema dirs (`alembic/`, `prisma/`, `*.sql`) | Absent. |
| Tests (`tests/`, `*.test.ts`, `*_test.py`) | Absent. |
| CI (`.github/workflows/`) | Absent. |
| Docker (`Dockerfile`, `docker-compose.yml`) | Absent. |

Negative results are part of the architecture. They constrain what this document is allowed to say.

---

## 3. Repository tree

```text
EquiClaim/
├── LICENSE                 # MIT, copyright 2026 I_blame_sumit
├── README.md               # public inventory + civic framing
└── docs/
    ├── ARCHITECTURE.md     # this file
    ├── state_diagram.md    # verified state machine (repo, not LangGraph)
    └── sequence_diagram.md # verified sequence (claim cannot enter a graph)
```

No `src/`, `backend/`, `frontend/`, `app/`, `packages/`, or `services/` directory exists.

---

## 4. AgentState / graph state schema and channels

**Not present.**

There is no `TypedDict`, `dataclass`, Pydantic model, MessagesState subclass, or annotation-reducer map that could be called AgentState.

| Channel | Type | Reducer | Source |
| --- | --- | --- | --- |
| — | — | — | *[NOT VERIFIED IN CODE — confirm before publishing]* |

Do not import a state schema from another denial-appeal or civic-tech repo and paste it here. When a graph module exists, copy field names from that file only.

---

## 5. Node responsibilities and edges

**Not present.**

No `StateGraph(...)`, `graph.add_node(...)`, `graph.add_edge(...)`, `graph.add_conditional_edges(...)`, or compiled `graph.invoke` / `graph.ainvoke` entrypoint exists.

| Node name | Responsibility | Outgoing edges | Source |
| --- | --- | --- | --- |
| — | — | — | *[NOT VERIFIED IN CODE — confirm before publishing]* |

[`state_diagram.md`](state_diagram.md) therefore does **not** contain invented node identifiers such as `intake`, `cross_examine`, or `emit_docket`. Those strings do not appear in this repository.

The only state machine that can be drawn without lying is the **repository lifecycle** (uninitialized application → license-only `main` → documentation branch). That is a git state machine, not an adjudication graph.

---

## 6. Mathematical / actuarial invariants

**Not present.**

No fee-schedule math, allowed-amount formula, QPA comparison, surprise-billing hold-harmless check, copay/coinsurance identity, or rounding rule is implemented. No test asserts an invariant.

| Invariant | Expression | Enforced in |
| --- | --- | --- |
| — | — | *[NOT VERIFIED IN CODE — confirm before publishing]* |

Public statutes (No Surprises Act, hospital MRF rules) exist outside this repo. Their existence in law is not the same as an encoded invariant. This document does not treat legislation as a unit test.

---

## 7. Database, indexing, PostgreSQL, checkpointing

**Not present.**

Searched for and not found: SQLAlchemy / Drizzle / Prisma models, `CREATE INDEX`, `AsyncPostgresSaver`, `PostgresSaver`, `SqliteSaver`, `MemorySaver`, connection-pool settings, quarantine tables, or any `DATABASE_URL` consumer.

| Concern | Status |
| --- | --- |
| Object-relational mapping | *[NOT VERIFIED IN CODE — confirm before publishing]* |
| Indexes | *[NOT VERIFIED IN CODE — confirm before publishing]* |
| LangGraph checkpointer | *[NOT VERIFIED IN CODE — confirm before publishing]* |
| Connection pooling | *[NOT VERIFIED IN CODE — confirm before publishing]* |
| Quarantine / dead-letter tables | *[NOT VERIFIED IN CODE — confirm before publishing]* |

If a later module uses `AsyncPostgresSaver.from_conn_string`, document the exact import path, the connection env var as read in that file, and whether `setup()` is called at process start. Until that file exists, claiming checkpointed graphs would be false.

---

## 8. API surface

**Not present.**

No ASGI/WSGI app, no Express/Fastify app, no Next.js route handlers, no OpenAPI spec.

| Method | Path | Handler file | Auth | Body model |
| --- | --- | --- | --- | --- |
| — | — | — | — | *[NOT VERIFIED IN CODE — confirm before publishing]* |

[`sequence_diagram.md`](sequence_diagram.md) shows an incoming claim dying at the boundary "no HTTP application." That is the real sequence.

---

## 9. Data ingestion (MRF, PFS, NCCI, CARC/RARC)

**Not present as code.**

These acronyms are domain language used in the project brief. They are not modules, parsers, or fixtures in this tree.

| Feed | What it would mean in a real system | In this repo |
| --- | --- | --- |
| Hospital / payer MRF | Machine-readable price files under CMS transparency rules | *[NOT VERIFIED IN CODE — confirm before publishing]* |
| PFS | Medicare Physician Fee Schedule | *[NOT VERIFIED IN CODE — confirm before publishing]* |
| NCCI | National Correct Coding Initiative edits | *[NOT VERIFIED IN CODE — confirm before publishing]* |
| CARC / RARC | Claim adjustment / remittance advice remark codes | *[NOT VERIFIED IN CODE — confirm before publishing]* |

Do not describe ingestion pipelines, refresh cadences, or "circuit breakers on CMS downloads" until a downloader and a failure path exist.

---

## 10. The one verified contract: MIT license

[`LICENSE`](../LICENSE) is the only source file with normative text.

| Clause | Meaning for an engineer |
| --- | --- |
| Copyright | `Copyright (c) 2026 I_blame_sumit` |
| Grant | Use, copy, modify, merge, publish, distribute, sublicense, sell |
| Condition | Keep the copyright and permission notice in copies |
| Warranty | **None.** Expressly no merchantability or fitness warranty |
| Liability | Authors not liable for claims arising from use |

There is no additional `NOTICE`, CLA, or dual-license file.

Implication: anyone may later add an engine under this license, but **this commit does not ship an engine**. Downstream users cannot "run EquiClaim" from `main` as of the audit SHA.

---

## 11. Trade-offs and failure modes (as coded)

Coded failure modes require code. The failure modes that exist today are environmental, not algorithmic.

| Failure | What happens | Evidence |
| --- | --- | --- |
| `pip install -r requirements.txt` | File not found | no `requirements.txt` |
| `npm install` | File not found | no `package.json` |
| Start API / worker | No entrypoint | no `main.py`, `server.py`, `app.ts`, scripts |
| POST a claim | No listener | no bind, no routes |
| Resume a LangGraph thread | No checkpointer, no thread id | no saver, no graph |
| Load `.env` | No template, no readers | no `.env.example` |

Circuit breakers, retries, quarantine tables, and pooling strategies: *[NOT VERIFIED IN CODE — confirm before publishing]*.

The documentation trade-off is explicit: this file is shorter on "how EquiClaim reasons" and longer on "what EquiClaim is not, yet." That is the failure mode reviewers will feel. The alternative — a plausible LangGraph mermaid copied from a tutorial — would survive a skim and fail a `rg`. Faculty who teach integrity should prefer the skim-failing version.

---

## 12. Intended product sentence (not an implementation)

The repository name and the documentation brief describe EquiClaim as an autonomous cross-examination engine for insurance denial adjudication and hospital price-transparency compliance.

That sentence is **product intent**. It is not a list of implemented nodes. It does not authorize documenting:

- a specific number of agents
- a specific model vendor
- a specific QPA or NSA calculation
- a specific "audited dispute docket" schema

When those exist, they will have types and tests. Until then they stay unmarked or marked `[NOT VERIFIED IN CODE — confirm before publishing]`.

---

## 13. Rewrite checklist (for the commit that adds source)

Replace this file's empty tables using only files from that commit:

1. Read every schema file completely before writing the data-model section.
2. Extract HTTP paths and methods from route definitions, not from comments.
3. Trace LangGraph `add_node` / `add_edge` / conditional maps; use **those** strings in Mermaid.
4. Pin versions from `requirements.txt` / `pyproject.toml` / `package.json` exactly.
5. Build the env table from `.env.example` plus actual `os.getenv` / settings objects.
6. Describe indexes, savers, and quarantine tables only if the DDL or ORM shows them.
7. Delete every `[NOT VERIFIED IN CODE]` row that you can now cite.
8. Keep any remaining unverified row labeled.

If this checklist is skipped, the documentation will be worse than silence.

---

## 14. Related public work (not this repo)

The author's other public GitHub projects (for example BioScan Intelligence and Red-Box) contain multi-agent or LangGraph code. **Those architectures are not EquiClaim's.** Importing their node names, ports, or env vars into this file would be a category error. This document does not describe them.

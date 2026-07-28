"""
Phase 3, Sprint 2 -- the first read-only API layer. See
FRONTEND_BACKEND_RECONCILIATION.md and API_CONTRACTS.md for the
requirements this implements against, and PHASE_3_SPRINT_2_REVIEW.md
for what was actually built and why.

Boundary, stated the same way queries/__init__.py states its own: this
package is read-only (no write routes), introduces no new stored
state, and duplicates no business logic already living in sync/,
rules/, or queries/ -- every route here is a thin translation from an
existing queries/ function's plain-dict output into an
API_CONTRACTS.md-shaped DTO (api/dtos.py), nothing more. Query
functions stay HTTP-agnostic on purpose; this package is the only place
that imports fastapi/pydantic.
"""

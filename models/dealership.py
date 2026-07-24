"""
PHASE 2 SCAFFOLDING -- not yet used. See models/vehicle.py for context.

A location/business unit within one operational deployment (currently:
Mark Auto Group -- Mark Kia, Mark Mazda, Mark Mitsubishi). This is
deliberately NOT a Tenant. See DATA_MODEL.md's "Tenant vs Dealership"
section for the full reasoning; the short version:

- Tenant (not modeled, not needed yet): a completely separate
  organization. Different tenants should never share data. No current
  customer needs this -- LotSync is not being built as public SaaS
  right now, and building tenant management, auth, billing, or routing
  with no current customer for it would be exactly the speculative
  infrastructure this project has repeatedly avoided elsewhere.
- Dealership (this model): a location/business unit inside one
  deployment. Vehicles legitimately move between dealerships (dealer
  trades, inventory transfers) while remaining the same physical
  vehicle -- dealership is a mutable, current attribute of a Vehicle,
  never part of its identity. See Vehicle.current_dealership_id.

If Tenant is ever introduced, Dealership becomes a child of it
(add a tenant_id field) -- this model doesn't need to change shape,
just gain a parent.

This model also gives the "how does a source record get attributed to
a dealership" problem a single home. That problem was previously
solved four separate times, ad hoc, once per source (Keyper's
unreliable System field -> prefix scoping; RecovR's Kia/MARK_AUTO
umbrella split -> subset detection; Tekion -> single-file scope;
RapidRecon -> prefix overlap). Each importer's attribution logic
should ultimately resolve to a Dealership record, not a bare string.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Dealership:
    dealership_id: Optional[str] = None
    name: Optional[str] = None            # e.g. "Mark Kia"
    brand: Optional[str] = None           # e.g. "Kia"
    # tenant_id intentionally absent -- see docstring. Add only if/when
    # Tenant is actually introduced; don't add it speculatively now.

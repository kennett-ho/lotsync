-- Sprint 05 (DealerDOH) -- the access model: organization, dealership
-- parentage, and user membership.
--
-- This is the moment DATA_MODEL.md's "Tenant vs Dealership (resolved)"
-- section anticipated: "If LotSync ever becomes a product sold to
-- unrelated dealer groups, Dealership gains a tenant_id and becomes a
-- child of Tenant -- that's the whole migration." Sprint 05 introduces
-- that parent under the name `organization` (the DealerDOH product
-- vocabulary for the same concept) and gives the EXISTING dealership
-- table its parent column -- deliberately NOT a new, duplicate
-- "store" table; dealership (migrations/0006) already IS the store
-- concept, exactly as models/dealership.py governs.
--
-- user_membership connects a Supabase Auth user to (organization,
-- dealership, role). Design constraints, per the Sprint 05 spec:
--
-- - auth_user_id is the Supabase Auth user UUID as TEXT. No FOREIGN
--   KEY: Supabase's auth.users lives in a schema this migration set
--   does not own (and does not exist at all under the SQLite engine),
--   and identity remains Supabase Auth's responsibility -- DealerDOH
--   stores no passwords, no tokens, no profile duplication.
-- - role is one of exactly four values, enforced by CHECK. The
--   authorization layer treats the membership row as the ONLY source
--   of a user's role -- never token metadata, never request input --
--   so an unknown/invalid role can only mean operator error, and the
--   CHECK surfaces that at write time instead of query time.
--   (employee.role, migrations/0006, is a different concept: an HR-ish
--   free-text job label on an operational Employee record. Membership
--   role is access control. They are deliberately separate columns on
--   deliberately separate tables.)
-- - active: memberships are deactivated, not deleted -- revoking
--   access should not erase the record that access once existed.
-- - UNIQUE(auth_user_id, dealership_id): one membership (one role)
--   per user per dealership. Role changes are an UPDATE, not a second
--   row, so authorization never has to disambiguate.

CREATE TABLE IF NOT EXISTS organization (
    organization_id  TEXT PRIMARY KEY,
    name             TEXT NOT NULL,
    created_at       TEXT NOT NULL DEFAULT (datetime('now'))
);

-- The anticipated "gains a parent" step. Nullable: pre-existing
-- dealership rows (and the production path, which never populates any
-- of this) remain valid without an organization.
ALTER TABLE dealership ADD COLUMN organization_id TEXT
    REFERENCES organization (organization_id);

CREATE TABLE IF NOT EXISTS user_membership (
    membership_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    auth_user_id     TEXT NOT NULL,
    organization_id  TEXT NOT NULL,
    dealership_id    TEXT NOT NULL,
    role             TEXT NOT NULL CHECK (role IN
                         ('admin', 'manager', 'lot_staff', 'sales_manager')),
    active           INTEGER NOT NULL DEFAULT 1,
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (auth_user_id, dealership_id),
    FOREIGN KEY (organization_id) REFERENCES organization (organization_id),
    FOREIGN KEY (dealership_id) REFERENCES dealership (dealership_id)
);

CREATE INDEX IF NOT EXISTS idx_user_membership_auth_user
    ON user_membership (auth_user_id);

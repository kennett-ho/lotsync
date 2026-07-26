-- Phase 2, Slice 6 -- Recommendation.
--
-- See DATA_MODEL.md's Recommendation entry for the full reasoning.
-- Summary: deliberately distinct from Task -- has its own lifecycle
-- (open / converted_to_task / dismissed) before ever becoming a Task.
-- Rule-driven (rules/aging.py, rules/inventory.py), not ML-driven.
--
-- created_at/resolved_at are additions beyond the originally documented
-- shape (see DATA_MODEL.md's note on each) -- needed to actually
-- implement "a dismissed Recommendation does not reappear unless the
-- underlying vehicle state genuinely changes again," which requires
-- knowing when a Recommendation was dismissed, not just that it was.
--
-- No FOREIGN KEY on resulting_task_id declared as NOT NULL-enforcing --
-- it's nullable and only ever set once (upon conversion), same pattern
-- as pending_identity.resolved_vin. A real FK IS declared here, though,
-- since (like escalated_from_task_id) the referenced Task always
-- already exists by the time a Recommendation converts into it.
--
-- No dealership_id -- see DATA_MODEL.md: a Recommendation always
-- reflects a Vehicle's CURRENT state, so dealership is always
-- derivable via vin, no historical-accuracy reason to duplicate it
-- (unlike Event).

CREATE TABLE IF NOT EXISTS recommendation (
    recommendation_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    vin                 TEXT NOT NULL,
    severity            TEXT,
    title               TEXT,
    detail              TEXT,
    rule_source         TEXT NOT NULL,
    status              TEXT NOT NULL DEFAULT 'open',
    resulting_task_id   INTEGER,
    created_at          TEXT NOT NULL,
    resolved_at         TEXT,
    FOREIGN KEY (vin) REFERENCES vehicle (vin),
    FOREIGN KEY (resulting_task_id) REFERENCES task (task_id)
);

CREATE INDEX IF NOT EXISTS idx_recommendation_vin ON recommendation (vin);
CREATE INDEX IF NOT EXISTS idx_recommendation_rule_source ON recommendation (rule_source);
CREATE INDEX IF NOT EXISTS idx_recommendation_status ON recommendation (status);

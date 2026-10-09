ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'auditor';

ALTER TABLE equipments
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS deleted_by INTEGER REFERENCES users(id);

UPDATE equipments SET is_active = TRUE WHERE is_active IS NULL;
ALTER TABLE equipments
    ALTER COLUMN is_active SET DEFAULT TRUE,
    ALTER COLUMN is_active SET NOT NULL;
CREATE INDEX IF NOT EXISTS ix_equipments_is_active ON equipments (is_active);

ALTER TABLE work_orders
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS deleted_by INTEGER REFERENCES users(id);

UPDATE work_orders SET is_active = TRUE WHERE is_active IS NULL;
ALTER TABLE work_orders
    ALTER COLUMN is_active SET DEFAULT TRUE,
    ALTER COLUMN is_active SET NOT NULL;

CREATE INDEX IF NOT EXISTS ix_work_orders_is_active ON work_orders (is_active);

CREATE TABLE IF NOT EXISTS audit_entries (
    id SERIAL PRIMARY KEY,
    record_type VARCHAR(30) NOT NULL,
    record_id INTEGER NOT NULL,
    action VARCHAR(30) NOT NULL,
    actor_id INTEGER NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    changes JSON NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_audit_entries_record
    ON audit_entries (record_type, record_id, created_at);

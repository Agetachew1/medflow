-- PostgreSQL schema for the current MedFlow SQLAlchemy models.
-- This script is additive and safe to rerun; it does not drop existing data.

DO $$
BEGIN
    CREATE TYPE equipment_status AS ENUM (
        'available',
        'in_use',
        'under_maintenance',
        'offline'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END;
$$;

DO $$
BEGIN
    CREATE TYPE work_order_priority AS ENUM ('low', 'medium', 'critical');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END;
$$;

DO $$
BEGIN
    CREATE TYPE "work_order_Status" AS ENUM (
        'pending',
        'in_progress',
        'completed',
        'failed'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END;
$$;

DO $$
BEGIN
    CREATE TYPE user_role AS ENUM (
        'clinical_admin',
        'field_technician',
        'hospital_manager',
        'auditor'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END;
$$;

ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'auditor';

CREATE TABLE IF NOT EXISTS hospitals (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    location_region VARCHAR(100) NOT NULL,
    capacity        INTEGER NOT NULL,
    supervisor_id   INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    username        VARCHAR(50) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role            user_role NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    hospital_id     INTEGER REFERENCES hospitals (id)
);

CREATE TABLE IF NOT EXISTS equipments (
    id            SERIAL PRIMARY KEY,
    serial_number VARCHAR(100) NOT NULL UNIQUE,
    model         VARCHAR(100) NOT NULL,
    status        equipment_status NOT NULL DEFAULT 'available',
    charge_level  NUMERIC(5, 2) NOT NULL,
    facility_id   INTEGER NOT NULL REFERENCES hospitals (id),
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    deleted_at    TIMESTAMPTZ,
    deleted_by    INTEGER REFERENCES users (id),
    CONSTRAINT charge_level_range CHECK (charge_level BETWEEN 0 AND 100)
);

CREATE TABLE IF NOT EXISTS work_orders (
    id            SERIAL PRIMARY KEY,
    title         VARCHAR(100) NOT NULL,
    priority      work_order_priority NOT NULL,
    status        "work_order_Status" NOT NULL DEFAULT 'pending',
    equipment_id  INTEGER NOT NULL REFERENCES equipments (id),
    technician_id INTEGER NOT NULL REFERENCES users (id),
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    deleted_at    TIMESTAMPTZ,
    deleted_by    INTEGER REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS service_reports (
    id            SERIAL PRIMARY KEY,
    work_order_id INTEGER NOT NULL REFERENCES work_orders (id),
    file_url      TEXT NOT NULL,
    notes         TEXT,
    created_at    TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    chain_id   VARCHAR(36) NOT NULL,
    issued_at  TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked    BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS audit_entries (
    id          SERIAL PRIMARY KEY,
    record_type VARCHAR(30) NOT NULL,
    record_id   INTEGER NOT NULL,
    action      VARCHAR(30) NOT NULL,
    actor_id    INTEGER NOT NULL REFERENCES users (id),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    changes     JSON NOT NULL
);

-- Bring older installations forward without dropping their existing records.
ALTER TABLE equipments
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS deleted_by INTEGER REFERENCES users (id);

ALTER TABLE work_orders
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS deleted_by INTEGER REFERENCES users (id);

UPDATE equipments SET is_active = TRUE WHERE is_active IS NULL;
ALTER TABLE equipments
    ALTER COLUMN is_active SET DEFAULT TRUE,
    ALTER COLUMN is_active SET NOT NULL;

UPDATE work_orders SET is_active = TRUE WHERE is_active IS NULL;
ALTER TABLE work_orders
    ALTER COLUMN is_active SET DEFAULT TRUE,
    ALTER COLUMN is_active SET NOT NULL;

CREATE INDEX IF NOT EXISTS ix_hospitals_id ON hospitals (id);
CREATE INDEX IF NOT EXISTS ix_hospitals_name ON hospitals (name);
CREATE INDEX IF NOT EXISTS ix_hospitals_location_region ON hospitals (location_region);
CREATE INDEX IF NOT EXISTS ix_hospitals_supervisor_id ON hospitals (supervisor_id);

CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username);

CREATE INDEX IF NOT EXISTS ix_equipments_model ON equipments (model);
CREATE INDEX IF NOT EXISTS ix_equipments_status ON equipments (status);
CREATE INDEX IF NOT EXISTS ix_equipments_charge_level ON equipments (charge_level);
CREATE INDEX IF NOT EXISTS ix_equipments_facility_id ON equipments (facility_id);
CREATE INDEX IF NOT EXISTS ix_equipments_is_active ON equipments (is_active);

CREATE INDEX IF NOT EXISTS ix_work_orders_title ON work_orders (title);
CREATE INDEX IF NOT EXISTS ix_work_orders_status ON work_orders (status);
CREATE INDEX IF NOT EXISTS ix_work_orders_equipment_id ON work_orders (equipment_id);
CREATE INDEX IF NOT EXISTS ix_work_orders_is_active ON work_orders (is_active);

CREATE INDEX IF NOT EXISTS ix_refresh_tokens_chain_id ON refresh_tokens (chain_id);
CREATE INDEX IF NOT EXISTS ix_refresh_tokens_user_id ON refresh_tokens (user_id);
CREATE INDEX IF NOT EXISTS ix_audit_entries_record
    ON audit_entries (record_type, record_id, created_at);

BEGIN;

UPDATE users
SET role = 'auditor'
WHERE role::text = 'hospital_manager';

ALTER TABLE users
    ALTER COLUMN role TYPE TEXT USING role::text;

ALTER TYPE user_role RENAME TO user_role_old;

CREATE TYPE user_role AS ENUM (
    'clinical_admin',
    'field_technician',
    'auditor'
);

ALTER TABLE users
    ALTER COLUMN role TYPE user_role USING role::user_role;

DROP TYPE user_role_old;

COMMIT;

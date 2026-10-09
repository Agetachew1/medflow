-- Run through bin/seed.sh, which supplies a bcrypt hash and the reset flag.
-- This seed is idempotent and only changes rows identified as MedFlow demo data.
BEGIN;

UPDATE hospitals AS hospital
SET location_region = seed.location_region,
    capacity = seed.capacity
FROM (
    VALUES
        ('Mercy General', 'Downtown', 250),
        ('St. Jude''s', 'Westside', 180),
        ('City Health', 'Northside', 140)
) AS seed(name, location_region, capacity)
WHERE hospital.name = seed.name;

INSERT INTO hospitals (name, location_region, capacity, supervisor_id)
SELECT seed.name, seed.location_region, seed.capacity, 1
FROM (
    VALUES
        ('Mercy General', 'Downtown', 250),
        ('St. Jude''s', 'Westside', 180),
        ('City Health', 'Northside', 140)
) AS seed(name, location_region, capacity)
WHERE NOT EXISTS (
    SELECT 1 FROM hospitals AS hospital WHERE hospital.name = seed.name
);

INSERT INTO users (username, hashed_password, role, hospital_id)
SELECT seed.username,
       :'seed_password_hash',
       seed.role::user_role,
       hospital.id
FROM (
    VALUES
        ('admin_abe', 'clinical_admin', 'Mercy General'),
        ('tech_john', 'field_technician', 'Mercy General'),
        ('tech_mike', 'field_technician', 'St. Jude''s'),
        ('auditor_amy', 'auditor', 'Mercy General')
) AS seed(username, role, hospital_name)
JOIN LATERAL (
    SELECT id
    FROM hospitals
    WHERE name = seed.hospital_name
    ORDER BY id
    LIMIT 1
) AS hospital ON TRUE
ON CONFLICT (username) DO UPDATE
SET role = EXCLUDED.role,
    hospital_id = EXCLUDED.hospital_id,
    hashed_password = CASE
        WHEN :'reset_seed'::BOOLEAN THEN EXCLUDED.hashed_password
        ELSE users.hashed_password
    END;

INSERT INTO equipments (
    serial_number, model, charge_level, status, facility_id, is_active
)
SELECT seed.serial_number,
       seed.model,
       seed.charge_level,
       seed.status::equipment_status,
       hospital.id,
       TRUE
FROM (
    VALUES
        ('MRI-001', 'Siemens Magnetom', 95, 'available', 'Mercy General'),
        ('XRY-002', 'GE Optima', 88, 'available', 'St. Jude''s'),
        ('ULT-003', 'Philips EPIQ', 12, 'available', 'City Health'),
        ('VEN-004', 'Medtronic Puritan', 5, 'available', 'Mercy General'),
        ('DEF-005', 'Zoll X Series', 100, 'under_maintenance', 'St. Jude''s'),
        ('DEF-006', 'Zoll X Series', 100, 'under_maintenance', 'St. Jude''s')
) AS seed(serial_number, model, charge_level, status, hospital_name)
JOIN LATERAL (
    SELECT id
    FROM hospitals
    WHERE name = seed.hospital_name
    ORDER BY id
    LIMIT 1
) AS hospital ON TRUE
ON CONFLICT (serial_number) DO UPDATE
SET model = EXCLUDED.model,
    charge_level = EXCLUDED.charge_level,
    status = EXCLUDED.status,
    facility_id = EXCLUDED.facility_id,
    is_active = TRUE,
    deleted_at = NULL,
    deleted_by = NULL;

WITH seed(title, serial_number, username, status, priority) AS (
    VALUES
        ('Routine Calibration', 'MRI-001', 'tech_john', 'pending', 'low'),
        ('Urgent Sensor Replacement', 'ULT-003', 'tech_mike', 'in_progress', 'critical'),
        ('Screen Fix', 'XRY-002', 'tech_john', 'completed', 'low'),
        ('Power Supply Swap', 'XRY-002', 'tech_john', 'failed', 'critical')
)
UPDATE work_orders AS work_order
SET status = seed.status::"work_order_Status",
    priority = seed.priority::work_order_priority,
    is_active = TRUE,
    deleted_at = NULL,
    deleted_by = NULL
FROM seed
JOIN equipments AS equipment ON equipment.serial_number = seed.serial_number
JOIN users AS technician ON technician.username = seed.username
WHERE work_order.title = seed.title
  AND work_order.equipment_id = equipment.id
  AND work_order.technician_id = technician.id;

WITH seed(title, serial_number, username, status, priority) AS (
    VALUES
        ('Routine Calibration', 'MRI-001', 'tech_john', 'pending', 'low'),
        ('Urgent Sensor Replacement', 'ULT-003', 'tech_mike', 'in_progress', 'critical'),
        ('Screen Fix', 'XRY-002', 'tech_john', 'completed', 'low'),
        ('Power Supply Swap', 'XRY-002', 'tech_john', 'failed', 'critical')
)
INSERT INTO work_orders (title, equipment_id, technician_id, status, priority)
SELECT seed.title,
       equipment.id,
       technician.id,
       seed.status::"work_order_Status",
       seed.priority::work_order_priority
FROM seed
JOIN equipments AS equipment ON equipment.serial_number = seed.serial_number
JOIN users AS technician ON technician.username = seed.username
WHERE NOT EXISTS (
    SELECT 1
    FROM work_orders AS existing
    WHERE existing.title = seed.title
      AND existing.equipment_id = equipment.id
      AND existing.technician_id = technician.id
);

COMMIT;

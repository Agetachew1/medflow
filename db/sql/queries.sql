-- Operational reporting queries for the MedFlow PostgreSQL schema.

-- Active equipment by facility and status.
SELECT hospital.name AS facility,
       equipment.status,
       COUNT(*) AS equipment_count
FROM equipments AS equipment
JOIN hospitals AS hospital ON hospital.id = equipment.facility_id
WHERE equipment.is_active IS TRUE
GROUP BY hospital.name, equipment.status
ORDER BY hospital.name, equipment.status;

-- Active equipment requiring attention because its charge is low.
SELECT equipment.id,
       equipment.serial_number,
       equipment.model,
       equipment.charge_level,
       hospital.name AS facility
FROM equipments AS equipment
JOIN hospitals AS hospital ON hospital.id = equipment.facility_id
WHERE equipment.is_active IS TRUE
  AND equipment.charge_level < 20
ORDER BY equipment.charge_level, equipment.serial_number;

-- Active work orders grouped by status and priority.
SELECT status,
       priority,
       COUNT(*) AS work_order_count
FROM work_orders
WHERE is_active IS TRUE
GROUP BY status, priority
ORDER BY status, priority;

-- Active workload by technician.
SELECT technician.username,
       hospital.name AS facility,
       COUNT(work_order.id) AS active_work_orders
FROM users AS technician
LEFT JOIN hospitals AS hospital ON hospital.id = technician.hospital_id
LEFT JOIN work_orders AS work_order
       ON work_order.technician_id = technician.id
      AND work_order.is_active IS TRUE
WHERE technician.role = 'field_technician'
  AND technician.is_active IS TRUE
GROUP BY technician.username, hospital.name
ORDER BY active_work_orders DESC, technician.username;

-- Recent service reports with their work order and equipment.
SELECT report.created_at,
       work_order.title AS work_order,
       equipment.serial_number,
       report.file_url,
       report.notes
FROM service_reports AS report
JOIN work_orders AS work_order ON work_order.id = report.work_order_id
JOIN equipments AS equipment ON equipment.id = work_order.equipment_id
WHERE work_order.is_active IS TRUE
  AND equipment.is_active IS TRUE
ORDER BY report.created_at DESC;

-- Chronological audit history for one record (set the two parameters first).
-- Replace the values below with 'equipment' or 'work_order' and the record ID.
SELECT audit.created_at,
       audit.record_type,
       audit.record_id,
       audit.action,
       actor.username AS actor,
       audit.changes
FROM audit_entries AS audit
JOIN users AS actor ON actor.id = audit.actor_id
WHERE audit.record_type = 'equipment'
  AND audit.record_id = 1
ORDER BY audit.created_at, audit.id;

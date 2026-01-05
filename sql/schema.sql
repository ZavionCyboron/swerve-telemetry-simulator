CREATE DATABASE IF NOT EXISTS swerve_sim;
USE swerve_sim;

CREATE TABLE IF NOT EXISTS swerve_tick (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    run_id CHAR(36) NOT NULL,
    elapsed_ms BIGINT NOT NULL,
    ts DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    tick INT NOT NULL,
    battery_v DOUBLE NOT NULL,
    vx_cmd DOUBLE NOT NULL,
    vy_cmd DOUBLE NOT NULL,
    omega_cmd DOUBLE NOT NULL,
    yaw_deg DOUBLE NOT NULL
);

CREATE TABLE IF NOT EXISTS swerve_module_tick (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    tick_id BIGINT NOT NULL,
    run_id CHAR(36) NOT NULL,
    module VARCHAR(2) NOT NULL,
    cmd_angle_deg DOUBLE NOT NULL,
    meas_angle_deg DOUBLE NOT NULL,
    cmd_rpm DOUBLE NOT NULL,
    meas_rpm DOUBLE NOT NULL,
    drive_applied_pct DOUBLE NOT NULL,
    turn_applied_pct DOUBLE NOT NULL,
    drive_current_a DOUBLE NOT NULL,
    turn_current_a DOUBLE NOT NULL,
    drive_temp_c DOUBLE NOT NULL,
    turn_temp_c DOUBLE NOT NULL,
    FOREIGN KEY (tick_id) REFERENCES swerve_tick(id)
);

-- Index: swerve_tick(ts)
SET @idx_exists := (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.STATISTICS
    WHERE table_schema = DATABASE()
      AND table_name = 'swerve_tick'
      AND index_name = 'idx_tick_ts'
);
SET @sql := IF(
        @idx_exists = 0,
        'CREATE INDEX idx_tick_ts ON swerve_tick(ts)',
        'SELECT ''Index idx_tick_ts already exists'' AS msg'
            );
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Index: swerve_tick(run_id, tick)
SET @idx_exists := (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.STATISTICS
    WHERE table_schema = DATABASE()
      AND table_name = 'swerve_tick'
      AND index_name = 'idx_run_tick'
);
SET @sql := IF(
        @idx_exists = 0,
        'CREATE INDEX idx_run_tick ON swerve_tick(run_id, tick)',
        'SELECT ''Index idx_run_tick already exists'' AS msg'
            );
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Index: swerve_module_tick(run_id, tick_id)  (best for joins)
SET @idx_exists := (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.STATISTICS
    WHERE table_schema = DATABASE()
      AND table_name = 'swerve_module_tick'
      AND index_name = 'idx_tickid_run'
);
SET @sql := IF(
        @idx_exists = 0,
        'CREATE INDEX idx_tickid_run ON swerve_module_tick(run_id, tick_id)',
        'SELECT ''Index idx_tickid_run already exists'' AS msg'
            );
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Index: swerve_module_tick(run_id, module, tick_id) (for per-module queries)
SET @idx_exists := (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.STATISTICS
    WHERE table_schema = DATABASE()
      AND table_name = 'swerve_module_tick'
      AND index_name = 'idx_run_module'
);
SET @sql := IF(
        @idx_exists = 0,
        'CREATE INDEX idx_run_module ON swerve_module_tick(run_id, module, tick_id)',
        'SELECT ''Index idx_run_module already exists'' AS msg'
            );
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
USE swerve_sim;

WITH
    latest AS (
        SELECT run_id
        FROM swerve_sim.swerve_tick
        GROUP BY run_id
        ORDER BY MAX(ts) DESC
        LIMIT 1
    ),
    ticks AS (
        SELECT
            id AS tick_id,
            run_id,
            tick,
            elapsed_ms,
            battery_v,
            FLOOR(tick / 100) + 1 AS tick_block
        FROM swerve_sim.swerve_tick
        WHERE run_id = (SELECT run_id FROM latest)
    ),
    mods AS (
        SELECT
            run_id,
            tick_id,
            module,
            meas_angle_deg,
            meas_rpm,
            drive_temp_c,
            turn_temp_c
        FROM swerve_sim.swerve_module_tick
        WHERE run_id = (SELECT run_id FROM latest)
    ),
    battery_block AS (
        SELECT
            tick_block,
            ROUND(AVG(battery_v), 3) AS avg_battery_v
        FROM ticks
        GROUP BY tick_block
    ),
    temp_block AS (
        SELECT
            t.tick_block,
            m.module,
            ROUND(AVG(m.drive_temp_c), 3) AS avg_drive_temp_c,
            ROUND(AVG(m.turn_temp_c), 3) AS avg_turn_temp_c
        FROM ticks t
                 JOIN mods m
                      ON m.tick_id = t.tick_id AND m.run_id = t.run_id
        GROUP BY t.tick_block, m.module
    )
SELECT
    t.tick,
    t.elapsed_ms,
    t.tick_block,

    m.module,
    m.meas_angle_deg,   -- precise per tick
    m.meas_rpm,         -- precise per tick

    bb.avg_battery_v,   -- avg per 100 ticks (robot-level)
    tb.avg_drive_temp_c, -- avg per 100 ticks per module
    tb.avg_turn_temp_c   -- avg per 100 ticks per module
FROM ticks t
         JOIN mods m
              ON m.tick_id = t.tick_id AND m.run_id = t.run_id
         JOIN battery_block bb
              ON bb.tick_block = t.tick_block
         JOIN temp_block tb
              ON tb.tick_block = t.tick_block AND tb.module = m.module
ORDER BY t.tick, m.module;
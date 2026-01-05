import time, random, math
from datetime import datetime
from dataclasses import dataclass
import mysql.connector
import uuid

MODULES = ["FL", "FR", "RL", "RR"]

@dataclass
class ModuleState:
    angle_deg: float = 0.0
    rpm: float = 0.0
    drive_temp_c: float = 0.0
    turn_temp_c: float = 0.0

DT = 0.005 # 200 Hz
MAX_TURN_RATE_DPS = 720.0           # deg/sec (tune)
TURN_TAU = 0.18                     # seconds (lag)
DRIVE_TAU = 0.25                    # seconds (lag)
MAX_RPM_DRIVE = 5676.0              # cap (tune)
MAX_RPM_LAUNCHER = 0.0              # not used here

def wrap_deg(deg: float) -> float:
    deg = (deg + 180.0) % 360.0 - 180.0
    return deg

def angel_error_deg(targe: float, current: float) -> float:
    return wrap_deg(targe - current)

def first_order_step(current: float, target: float, tau: float, dt: float) -> float:
    # simple lag model
    alpha = dt / max(tau, 1e-6)
    if alpha > 1.0:
        alpha = 1.0
    return current + (target - current) * alpha

def simulate_driver_command(t: float):
    # simple “match-like” pattern
    # vx, vy in [-1..1] scaled later; omega in [-1..1]
    vx = 0.8 * math.sin(t * 0.3)
    vy = 0.6 * math.cos(t * 0.23)
    omega = 0.4 * math.sin(t * 0.17)
    return vx, vy, omega

def cmd_to_module_setpoints(vx, vy, omega):
    """
    Not full kinematics-just create per-module target angles/speeds that change with vx/vy/omega.
    This is enough to generate believable telemetry
    """
    base_speed = math.sqrt(vx**2 + vy**2)
    base_angle = math.degrees(math.atan2(vy, vx)) if base_speed > 0.02 else 0.0

    # give each module slightly different effect from omega
    omega_offsets = {"FL": +omega, "FR": -omega, "RL": -omega, "RR": +omega}

    out = {}
    for m in MODULES:
        # angle shifts with omega a bit
        ang = wrap_deg(base_angle + omega_offsets[m] * 35.0)
        # speed changes with omega a bit
        spd = max(0.0, min(1.0, base_speed + abs(omega_offsets[m]) * 0.15))
        rpm = spd * MAX_RPM_DRIVE
        out[m] = (ang, rpm)
    return out

def connect():
    return mysql.connector.connect(
        host="localhost",
        port=3306,
        user="root",
        password="Kensla85!",
        database="swerve_sim",
        autocommit=False
    )

def main(seconds=50, max_ticks=10000):
    start_time = time.perf_counter()
    db = connect()
    cur = db.cursor()
    run_id = str(uuid.uuid4())
    print("run_id:", run_id)

    # persistent states
    states = {m: ModuleState() for m in MODULES}
    yaw_deg = 0.0

    tick_sql = """
    INSERT INTO swerve_tick (run_id, ts, elapsed_ms, tick, battery_v, vx_cmd, vy_cmd, omega_cmd, yaw_deg)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    mod_sql = """
    INSERT INTO swerve_module_tick
    (run_id, tick_id, module, cmd_angle_deg, meas_angle_deg, cmd_rpm, meas_rpm,
     drive_applied_pct, turn_applied_pct, drive_current_a, turn_current_a,
     drive_temp_c, turn_temp_c)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    t0 = time.time()
    tick = 0

    print("Running swerve simulation... (stop with the Pycharm stop button if needed)")
    try:
        while time.time() - t0 < seconds and tick <= max_ticks:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            t = time.time() - t0
            vx, vy, omega = simulate_driver_command(t)

            setpoints = cmd_to_module_setpoints(vx, vy, omega)

            # rough yaw integration with noise
            yaw_deg = wrap_deg(yaw_deg + omega * 90.0 * DT + random.uniform(-0.2, 0.2))

            # compute per-module updates + rough current sum
            module_rows = []
            total_current = 0.0

            for m, (cmd_ang, cmd_rpm) in setpoints.items():
                s = states[m]

                # turning dynamics
                err = angel_error_deg(cmd_ang, s.angle_deg)
                # cap rate
                desired_turn_step = max(-MAX_TURN_RATE_DPS*DT, min(MAX_TURN_RATE_DPS*DT, err))
                s.angle_deg = wrap_deg(s.angle_deg + desired_turn_step * (DT / max(TURN_TAU, 1e-6)))

                # drive dynamics (lag)
                s.rpm = first_order_step(s.rpm, cmd_rpm, DRIVE_TAU, DT)

                # add small measurement noise
                meas_ang = round(wrap_deg(s.angle_deg + random.uniform(-0.8, 0.8)), 3)
                meas_rpm = round(max(0.0, s.rpm + random.uniform(-40.0, 40.0)), 2)

                # “applied output” approximations
                drive_applied = 0.0 if MAX_RPM_DRIVE == 0 else (cmd_rpm / MAX_RPM_DRIVE)
                turn_applied = max(-1.0, min(1.0, err / 90.0))

                # crude currents: higher when accelerating or large error
                drive_current = 8.0 + abs(cmd_rpm - s.rpm) * 0.01 + abs(drive_applied) * 20.0
                turn_current = 3.0 + abs(err) * 0.05

                total_current += drive_current + turn_current

                # temps rise with current
                s.drive_temp_c += (drive_current * 0.002) - 0.01
                s.turn_temp_c += (turn_current * 0.003) - 0.01

                module_rows.append((m, cmd_ang, meas_ang, cmd_rpm, meas_rpm,
                                    drive_applied, turn_applied, drive_current, turn_current,
                                    s.drive_temp_c, s.turn_temp_c))

            # battery sag model
            battery_v = round(max(8.5, 12.6 - total_current * 0.01), 2)

            # insert tick row
            ts = datetime.now()
            cur.execute(tick_sql, (run_id, ts, elapsed_ms, tick, battery_v, vx, vy, omega, yaw_deg))
            tick_id = cur.lastrowid

            # insert module rows
            cur.executemany(mod_sql, [(run_id, tick_id, *r) for r in module_rows])
            db.commit()

            if tick % 100 == 0:
                print(f"tick={tick} battery={battery_v:.2f}V inserted 1 tick + 4 modules")

            tick += 1
            time.sleep(DT)

    finally:
        cur.close()
        db.close()

if __name__  == "__main__":
    main(seconds=90, max_ticks=10000)

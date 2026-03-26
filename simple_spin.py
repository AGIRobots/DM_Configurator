import time

from DM_CAN import MotorControl, Motor, DM_Motor_Type, Control_Type

# === User configuration ===
SERIAL_PORT = '/dev/ttyACM4'  # Change to your serial port
MOTOR_TYPE = DM_Motor_Type.DM4310.value  # change if different
SLAVE_ID = 0x001           # set to your motor's slave ID
TARGET_VEL = 1.5           # rad/s (start small!)
RUNTIME_SEC = 5.0           # how long to hold the command
RECV_INTERVAL = 0.05        # seconds between polling recv()
# ==========================


def main():
    mc = MotorControl(SERIAL_PORT, MOTOR_TYPE, SLAVE_ID)
    motor = Motor(MOTOR_TYPE, SLAVE_ID, SLAVE_ID)
    mc.addMotor(motor)
    mc.switchControlMode(motor, Control_Type.VEL)

    try:
        print('Setting zero position (safety)')
        mc.set_zero_position(motor)
        time.sleep(0.1)

        print('Enabling motor')
        mc.enable(motor)
        time.sleep(0.2)

        print(f'Commanding velocity {TARGET_VEL} rad/s for {RUNTIME_SEC} seconds')
        mc.control_Vel(motor, TARGET_VEL)

        t0 = time.time()
        while time.time() - t0 < RUNTIME_SEC:
            mc.recv()
            mc.control_Vel(motor, TARGET_VEL)
            pos = motor.getPosition()
            vel = motor.getVelocity()
            tau = motor.getTorque()
            print(f'pos={pos:.4f} vel={vel:.4f} tau={tau:.4f}')
            time.sleep(RECV_INTERVAL)

        print('Stopping motor (set velocity 0)')
        mc.control_Vel(motor, 0.0)
        time.sleep(0.1)

    except KeyboardInterrupt:
        print('Interrupted by user, stopping')
        mc.control_Vel(motor, 0.0)
        time.sleep(0.1)
    except Exception as e:
        print('Error during motor operation:', e)
        try:
            mc.control_Vel(motor, 0.0)
            time.sleep(0.1)
        except Exception:
            pass
    finally:
        print('Disabling motor and closing connection')
        try:
            mc.disable(motor)
        except Exception:
            pass
        mc.close()


if __name__ == '__main__':
    main()
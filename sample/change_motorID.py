from DM_CAN import MotorControl, Motor, DM_Motor_Type, DM_variable

# === User configuration ===
SERIAL_PORT = '/dev/ttyACM4'
MOTOR_TYPE = DM_Motor_Type.DM4310.value
BEFORE_SLAVE_ID = 0x001
AFTER_SLAVE_ID = 0x002
# ==========================

def main():
    mc = MotorControl(SERIAL_PORT, MOTOR_TYPE, BEFORE_SLAVE_ID)
    motor = Motor(MOTOR_TYPE, BEFORE_SLAVE_ID, BEFORE_SLAVE_ID)
    mc.addMotor(motor)

    try:
        print(f"Changing motor ID from {BEFORE_SLAVE_ID} to {AFTER_SLAVE_ID}")
        mc.change_motor_param(motor, DM_variable.ESC_ID, AFTER_SLAVE_ID)
        print("Motor ID change command sent. Please power cycle the motor and run with the new ID.")
    except Exception as e:
        print('Error during motor ID change:', e)

    motor = Motor(MOTOR_TYPE, AFTER_SLAVE_ID, AFTER_SLAVE_ID);

    try:
        print("Save parameters to flash")
        mc.save_motor_param(motor)
    except Exception as e:
        print('Error saving to flash:', e)

    print('Closing connection')
    mc.close()

if __name__ == '__main__':
    main()
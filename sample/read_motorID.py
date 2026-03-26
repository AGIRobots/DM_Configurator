import sys
from DM_CAN import MotorControl, Motor, DM_Motor_Type, DM_variable


def main(SERIAL_PORT='/dev/ttyACM0', SLAVE_ID=0x001, MOTOR_TYPE=DM_Motor_Type.DM4310.value):
    mc = MotorControl(SERIAL_PORT, MOTOR_TYPE, SLAVE_ID)
    motor = Motor(MOTOR_TYPE, SLAVE_ID, SLAVE_ID)
    mc.addMotor(motor)

    try:
        print(f"Current motor ID: {mc.read_motor_param(motor, DM_variable.ESC_ID)}")
    except Exception as e:
        print('Error reading motor parameters:', e)
    finally:
        print('Closing connection')
        mc.close()

if __name__ == '__main__':
    args = sys.argv[1:]  # Skip script name
    if len(args) == 0:
        main()
    elif len(args) == 3:
        SERIAL_PORT = args[0]
        MOTOR_TYPE = int(args[1])
        SLAVE_ID = int(args[2], 0)  # auto-detect hex if prefixed with 0x
        main(SERIAL_PORT, SLAVE_ID, MOTOR_TYPE)
    else:        
        print("Usage: python read_motorID.py [SERIAL_PORT MOTOR_TYPE SLAVE_ID]")
        print("Example: python read_motorID.py /dev/ttyACM0 2 0x001")
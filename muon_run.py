import sys
import glob
import serial
from time import sleep
import logging
from data_collector import DataCollector


def serial_ports():
    """ Obtain a list of available serial port names.
    :returns: list of the serial ports.
    """
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # This excludes your current terminal "/dev/tty".
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')
    result = []
    # Iterate through possible com ports to see if any are available.
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result


# def select_port():
#     """Select detector communication port.
#
#     :return: port_name.
#     """
#     #print('Available serial ports:\n')
#     #print("[Q] Quit")
#     #for i in range(len(port_list)):
#     #    print('[' + str(i+1)+'] ' + str(port_list[i]))
#     port = input("Select the port connected to the Arduino: ")
#     port_name = str(port_list[int(port)-1])
#     print("The selected port is: " + port_name +'\n')
#     return port_name

def user_interact_part_one():
    print(f"Host platform: {sys.platform}")
    print("Connect the S detector to a serial port on the host.")
    s_name = input("Enter the name of your S detector (if set) else select [return] to continue: ")
    if s_name != "":
        print(f"Acquisition will only start when the host detects '{s_name}' from connected detector.")

    # option = input("Select [C] to continue or [Q] to : ")
    # if option.upper() != 'C':
    #     sys.exit(0)

    print('\nAvailable serial ports:')
    available_ports = serial_ports()
    for i, port_name in enumerate(available_ports):
        print(f"[{i+1}] {port_name}")
    print("[Q] Quit")
    option = input("Identify which serial port is connected to the S detector or Q to quit: ")
    if not option.isdigit() or abs(int(option)) > len(available_ports):
        sys.exit(0)
    return s_name, available_ports[int(option)-1]


def user_interact_part_two() -> bool:
    print("Reset the M detector and then the S detector.")
    print("Confirm that the detector displaying 'S---' is the one connected to the serial port.")
    option = input("Select [return] to continue or [Q] to quit: ")
    if option.upper() != '':
        return False
    return True


def set_logging():
    """Set logging configuration."""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s, %(levelname)s, %(message)s',
        datefmt='%Y-%m-%d:%H:%M:%S',
        handlers=[
            logging.FileHandler('C:/Users/dave/Temp/muon_log.txt'),
            logging.StreamHandler()
        ]
    )


def run():

    set_logging()
    logging.info('Starting up')
    s_name, port_name = user_interact_part_one()
    print(f"{port_name} selected")

    com_port = serial.Serial(port_name)
    com_port.baudrate = 9600
    com_port.bytesize = 8
    com_port.parity = 'N'
    com_port.stopbits = 1

    dc = DataCollector(com_port=com_port,
                       save_dir='C:/Users/dave/Temp/muon_data',
                       buff_size=200,
                       window_size=10,
                       log_all_events=True,
                       start_string=s_name)

    if not user_interact_part_two():
        com_port.close()
        sys.exit(0)

    dc.acquire_data(raw_dump=False)
    while not dc.acquisition_ended:
        sleep(0.01)


if __name__ == '__main__':
    run()


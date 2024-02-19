import sys
import glob
import serial
from time import sleep
from data_collector import DataCollector


def serial_ports():
    """ Obtain a list of available serial port names.
    :returns: list of the serial ports.
    """
    print(f"Platform: {sys.platform}")
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

def user_interact():

    print('Available serial ports:\n')
    available_ports = serial_ports()
    for i, port_name in enumerate(available_ports):
        print(f"[{i+1}] {port_name}")
    print("[Q] Quit")
    option = input("Select port connected to slave detector: ")
    if not option.isdigit() or abs(int(option)) > len(available_ports):
        sys.exit(0)

    print("GO!!!")
    return available_ports[int(option)-1]


def run():
    port_name = user_interact()
    print(f"{port_name} selected")

    com_port = serial.Serial(port_name)
    com_port.baudrate = 9600
    com_port.bytesize = 8
    com_port.parity = 'N'
    com_port.stopbits = 1

    dc = DataCollector(com_port=com_port,
                       save_dir=None,
                       buff_size=100,
                       window_size=10)

    dc.acquire_data(raw_dump=True)
    while not dc.acquisition_ended:
        sleep(0.01)

if __name__ == '__main__':
    run()


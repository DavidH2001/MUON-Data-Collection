import sys
import glob
import serial
from data_collector import DataCollector

def serial_ports():
    """ Lists serial port names.

    :raises EnvironmentError: on unsupported or unknown platforms
    :returns: a list of the serial ports available on the system
    """
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')
        sys.exit(0)
    result = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result


def select_port():
    """Select detector communication port.

    :return: port_name.
    """
    port_list = serial_ports()
    print('Available serial ports:\n')
    for i in range(len(port_list)):
        print('[ ' + str(i+1)+'] ' + str(port_list[i]))
    print('[h] help\n')
    port = input("Select Arduino Port: ")
    port_name = str(port_list[int(port)-1])
    print("The selected port is: " + port_name +'\n')
    return port_name


port_name = select_port()
com_port = serial.Serial(port_name)
com_port.baudrate = 9600
com_port.bytesize = 8
com_port.parity = 'N'
com_port.stopbits = 1

data_collector = DataCollector(com_port)

start_up(port_name,
         '../../Temp/data.txt',
         'Dodge',
         True)
acquire_data(save_results=True)
com_port.close()
data_file.close()
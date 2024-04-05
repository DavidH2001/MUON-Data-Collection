import math
import os.path
import sys
import glob
import json
from datetime import datetime, timezone
import serial
from time import sleep
import logging
from ftplib import FTP
from data_collector import DataCollector

VERSION: str = "0.1.0"


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


def user_interact_part_one():
    print(f"Host platform: {sys.platform}")
    print("Connect the S detector to a serial port on the host.")
    s_name = input("Enter the name of your S detector (if set) else [return] to continue or [Q] to quit: ")
    if s_name.upper() == "Q":
        sys.exit(0)
    if s_name != "":
        print(f"Acquisition will only start when the host detects '{s_name}' from connected detector.")

    print('\nAvailable serial ports:')
    available_ports = serial_ports()
    for i, port_name in enumerate(available_ports):
        print(f"[{i + 1}] {port_name}")
    print("[Q] Quit")
    option = input("Identify which serial port is connected to the S detector or Q to quit: ")
    if not option.isdigit() or abs(int(option)) > len(available_ports):
        sys.exit(0)
    return s_name, available_ports[int(option) - 1]


def user_interact_part_two() -> bool:
    print("Reset the M detector and then the S detector.")
    print("Confirm that the detector displaying 'S---' is the one connected to the serial port.")
    option = input("Select [return] to continue or [Q] to quit: ")
    if option.upper() != '':
        return False
    return True


def set_logging(root_dir: str, level: str) -> None:
    """Set logging configuration."""
    logging.basicConfig(
        level=logging.DEBUG if level.upper() == "DEBUG" else logging.INFO,
        format='%(asctime)s, %(levelname)s, %(message)s',
        datefmt='%Y-%m-%d:%H:%M:%S',
        handlers=[
            logging.FileHandler(os.path.join(root_dir, "muon_log.txt")),
            logging.StreamHandler()
        ]
    )


def _check_config(config):
    """Check the contents of the configuration file."""
    if ("event_files" not in config or "root_dir" not in config["event_files"] or
            config["event_files"]["root_dir"] == ""):
        raise ValueError("Please edit config.json to define the required root directory for logging event files.")
    root_dir = os.path.expanduser(config["event_files"]["root_dir"])
    if not os.path.exists(root_dir):
        raise ValueError(f"The root_dir '{root_dir}' defined in config.json does not exist.")
    if ("user" not in config or "latitude" not in config["user"] or "longitude" not in config["user"] or
            (math.isclose(config["user"]["latitude"], 0.0) and math.isclose(config["user"]["longitude"], 0.0) or not
                isinstance(config["user"]["latitude"], float) or not isinstance(config["user"]["longitude"], float))):
        raise ValueError("Please edit config.json to define the user latitude and longitude decimal values.")
    if "system" not in config or not isinstance(config["system"], dict):
        raise ValueError("Invalid config.json file detected.")
    if "buff_size" not in config["system"] or not isinstance(config["system"]["buff_size"], int):
        raise ValueError("The system buff_size parameter in config.json is missing or defined with incorrect type.")
    if "window_size" not in config["system"] or not isinstance(config["system"]["window_size"], int):
        raise ValueError("The system window_size parameter in config.json is missing or defined with incorrect type.")
    if "anomaly_threshold" not in config["system"] or not isinstance(config["system"]["anomaly_threshold"], float):
        raise ValueError("The system anomaly_threshold parameter in config.json is missing or defined with incorrect "
                         "type.")


def _check_ftp_connect(user_name: str, user_password: str, user_id: str, ip_address: str) -> None:
    """Check FTP connection and initial setup."""
    logging.info(f"Checking FTP connection for user folder {user_id}. Waiting for response...")
    try:
        with FTP(ip_address, user_name, user_password) as ftp:
            if user_id in ftp.nlst():
                logging.info("Remote user directory found.")
            else:
                logging.info(f"Welcome! Creating remote user directory {user_id}.")
                ftp.mkd(user_id)
    except TimeoutError:
        logging.error("Timeout - unable to connect with remote FTP server")


def run():
    """Main"""
    print(f"Muon data collection and anomaly detection V{VERSION}")
    # get configuration information
    with open("config.json") as json_data_file:
        config = json.load(json_data_file)
    _check_config(config)

    root_dir = os.path.expanduser(config['event_files']['root_dir'])
    user_id = f"{config['user']['name']}-{str(config['user']['latitude'])}-{str(config['user']['longitude'])}"
    user_id = user_id.replace('.', '-')
    print(f"user_id={user_id}")

    # setup logging
    log_level = config.get("system", None).get("logging_level", "INFO")
    start_time = datetime.now(timezone.utc).strftime("%y%m%d_%H%M%S")
    root_dir = os.path.join(root_dir, start_time)
    if not os.path.exists(root_dir):
        os.mkdir(root_dir)
    set_logging(root_dir, log_level)

    _check_ftp_connect(config['user']['name'], config['user']['password'], user_id, config['remote']['ip_address'])

    s_name, port_name = user_interact_part_one()
    print(f"{port_name} selected")

    com_port = serial.Serial(port_name, timeout=0.1)
    com_port.baudrate = 9600
    com_port.bytesize = 8
    com_port.parity = 'N'
    com_port.stopbits = 1

    buff_size = config.get("system", None).get("buff_size", 200)
    window_size = config.get("system", None).get("window_size", 10)
    anomaly_threshold = config.get("system", None).get("anomaly_threshold", 2.0)

    dc = DataCollector(com_port=com_port,
                       save_dir=root_dir,
                       buff_size=buff_size,
                       window_size=window_size,
                       anomaly_threshold=anomaly_threshold,
                       log_all_events=True,
                       start_string=s_name,
                       user_id=user_id,
                       user_name=config['user']['name'],
                       user_password=config['user']['password'],
                       ip_address=config['remote']['ip_address'])

    if not user_interact_part_two():
        com_port.close()
        sys.exit(0)

    logging.info(f'Starting {VERSION} using {log_level} logging level')
    logging.info(f"buff_size={buff_size}, window_size={window_size}, anomaly_threshold={anomaly_threshold}")
    logging.info(f"latitude={config['user']['latitude']}, longitude={config['user']['longitude']}")
    dc.acquire_data()
    dc.run_remote()
    logging.info("Bypassing header lines...")
    while not dc.processing_ended:
        sleep(0.01)
    logging.info("Shutdown complete")


if __name__ == '__main__':
    run()

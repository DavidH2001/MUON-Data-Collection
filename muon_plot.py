import copy
import os.path
import pandas as pd
import json
from os import listdir
from data_collector import VERSION, DATE_TIME_FORMAT
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import Tuple

"""
MUON data collection project.
Plotting utility.  
Original development by Dave Hardwick
"""

date_time_format: str = "%Y%m%d %H%M%S.%f"


def _add_datetime_column(buff: pd.DataFrame, start_event: int, start_datetime) -> None:
    """Calculate and add column representing UTC time for each event."""
    # TODO this function is not used. Delete if not implemented soon.
    start_event_row = buff[buff['event'] == start_event]
    start_time = (start_event_row['arduino_time'] - start_event_row['dead_time']).values[0]
    datetime_column = [start_datetime + timedelta(milliseconds=int((x['arduino_time'] - x['dead_time']) - start_time))
                       for _, x in buff[['arduino_time', 'dead_time']].iterrows()]
    buff['utc_time'] = datetime_column


def _read_csv(file_path) -> Tuple[pd.DataFrame, dict]:
    """Read event data from CSV file."""
    with open(file_path, 'r') as f:
        line = f.readline().rstrip('\n')
        line_list = line.split(sep=',')
    metadata = {"user_id": line_list[1], "Bn": line_list[2], "Wn": line_list[3], "threshold": line_list[4]}
    df = pd.read_csv(file_path, skiprows=1)
    return df, metadata


def get_data_file(file_path: str) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    """
    Get data from a specified file.
    :param file_path: data file.
    :return:
    """
    print(file_path)
    df, metadata = _read_csv(file_path)
    win_f_df = df.loc[df['win_f'].notna()]
    median_f_df = df.loc[df['median_f'].notna()]
    sipm_df = df[['comp_time', 'sipm']]
    return win_f_df, median_f_df, sipm_df, metadata


def get_data_dir(directory: str) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    """
    Get all event data from a specified directory.
    :param directory: root directly holding the event data.
    :return:
    """
    file_list = [file for file in listdir(directory) if file.endswith('csv')]
    win_f_df = None
    median_f_df = None
    sipm_df = None
    first_metadata = None
    for i, file in enumerate(file_list):
        win_f, median_f, sipm, metadata = get_data_file(os.path.join(directory, file))
        # extract frequency rows
        if i == 0:
            first_metadata = copy.deepcopy(metadata)
            win_f_df = win_f
            median_f_df = median_f
            sipm_df = sipm
        else:
            if metadata != first_metadata:
                raise ValueError(f"The event buffer file {file} metadata is not consistent with previous file(s).")
            win_f_df = pd.concat([win_f_df, win_f], ignore_index=True)
            median_f_df = pd.concat([median_f_df, median_f], ignore_index=True)
            sipm_df = pd.concat([sipm_df, sipm])

    win_f_df.insert(0, 'time', pd.to_datetime(win_f_df['comp_time'], format=date_time_format))
    win_f_df = win_f_df.sort_values(by='time', ignore_index=True)
    median_f_df.insert(0, 'time', pd.to_datetime(median_f_df['comp_time'], format=date_time_format))
    median_f_df = median_f_df.sort_values(by='time', ignore_index=True)
    sipm_df.insert(0, 'time', pd.to_datetime(sipm_df['comp_time'], format=date_time_format))
    sipm_df = sipm_df.sort_values(by='time', ignore_index=True)
    return win_f_df, median_f_df, sipm_df, first_metadata


def get_data_dirs(dir_list: list, sub_folder: str = None) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    """
    Get data from all listed directories.
    :param dir_list:
    :param sub_folder:
    :return:
    """
    win_f_df = None
    median_f_df = None
    sipm_df = None
    for i, directory in enumerate(dir_list):
        print(directory)
        if not os.path.isdir(os.path.join(directory, sub_folder)):
            continue
        win_f, median_f, sipm, metadata = get_data_dir(os.path.join(directory, sub_folder))
        if i == 0:
            win_f_df = win_f
            median_f_df = median_f
            sipm_df = sipm
        else:
            win_f_df = pd.concat([win_f_df, win_f])
            median_f_df = pd.concat([median_f_df, median_f])
            sipm_df = pd.concat([sipm_df, sipm])
    return win_f_df, median_f_df, sipm_df, metadata


def main():

    print(f"Muon data collection and anomaly detection V{VERSION}")

    with open("config.json") as json_data_file:
        config = json.load(json_data_file)

    # Select folder(s) to be accessed for event data. The root folder defined by the configuration is used by default:
    root_dir = os.path.expanduser(config['event_files']['root_dir'])
    # Alternatively, you can point to the project example data directory as shown here:
    # root_dir = "data"
    # Set single folder name here or leave empty for all folders to be accessed under root directory:
    single_dir_name = ""
    directory_list = [os.path.join(root_dir, single_dir_name)]
    # all folders
    if not single_dir_name:
        directory_list = [os.path.join(root_dir, name) for name in os.listdir(root_dir) if
                          os.path.isdir(os.path.join(root_dir, name))]

    # set up for plotting
    _, (ax1, ax2) = plt.subplots(nrows=2, sharex=True)

    # all event plotting
    ax1_2 = ax1.twinx()
    ax1.set_xlabel('Date/Time (UTC)')
    ax1.set_ylabel('Window Freq (Hz)')
    ax1_2.set_ylabel('SIPM (mV)')
    win_f_df, _, sipm, metadata = get_data_dirs(directory_list, "all")
    if win_f_df is not None:
        ax1.plot(win_f_df['time'].values, win_f_df['win_f'].values, '-', color='silver')
        ax1.plot(win_f_df['time'].values, win_f_df['median_f'].values, '+', color='gray')
        ax1_2.plot(sipm['time'].values, sipm['sipm'].values, '.', color='red', markersize=3, alpha=0.3)
    ax1.grid()
    ax1.set_title(f"All Buffers [{metadata['user_id']}  Bn:{metadata['Bn']}  Wn:{metadata['Wn']}  "
                  f"Thresh:{metadata['threshold']}]", fontsize=9)

    # anomaly plotting
    ax2_2 = ax2.twinx()
    ax2_2.set_ylabel('SIPM (mV)')

    # anomaly event plotting
    ax2.set_xlabel('Date/Time (UTC)')
    ax2.set_ylabel('Window Freq (Hz)')
    win_f_df, _, sipm, metadata = get_data_dirs(directory_list, "anomaly")
    if win_f_df is not None:
        ax2_2.set_ylim(ax1_2.get_ylim())
        ax2.plot(win_f_df['time'].values, win_f_df['win_f'].values, '-', color='silver')
        ax2_2.plot(sipm['time'].values, sipm['sipm'].values, '.', color='red', markersize=3, alpha=0.3)
    ax2.grid()
    ax2.set_title(f"Anomaly Buffers [{metadata['user_id']}  Bn:{metadata['Bn']}  Wn:{metadata['Wn']}  "
                  f"Thresh:{metadata['threshold']}]", fontsize=9)

    plt.tight_layout()
    plt.gcf().autofmt_xdate()
    plt.show()


if __name__ == "__main__":
    main()




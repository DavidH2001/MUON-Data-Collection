import os.path
import pandas as pd
import json
from os import listdir
from data_collector import VERSION
import matplotlib.pyplot as plt

"""
MUON data collection project.
Plotting utility.  
Original development by Dave Hardwick
"""

date_time_format: str = "%Y%m%d %H%M%S.%f"


def get_data_file(file: str) -> (pd.DataFrame, pd.DataFrame, pd.DataFrame):
    """
    Get data from a specified file.
    :param file: data file.
    :return:
    """
    print(file)
    df = pd.read_csv(file, skiprows=1)
    win_f_df = df.loc[df['win_f'].notna()]
    median_f_df = df.loc[df['median_f'].notna()]
    sipm_df = df[['comp_time', 'sipm']]

    return win_f_df, median_f_df, sipm_df


def get_data_dir(dir: str) -> (pd.DataFrame, pd.DataFrame, pd.DataFrame):
    """
    Get all event data from a specified directory.
    :param dir: root directly holding the event data.
    :return:
    """
    file_list = [file for file in listdir(dir) if file.endswith('csv')]
    win_f_df = None
    median_f_df = None
    sipm_df = None
    for i, file in enumerate(file_list):
        win_f, median_f, sipm = get_data_file(os.path.join(dir, file))
        # extract frequency rows
        if i == 0:
            win_f_df = win_f
            median_f_df = median_f
            sipm_df = sipm
        else:
            win_f_df = pd.concat([win_f_df, win_f], ignore_index=True)
            median_f_df = pd.concat([median_f_df, median_f], ignore_index=True)
            sipm_df = pd.concat([sipm_df, sipm])

    win_f_df.insert(0, 'time', pd.to_datetime(win_f_df['comp_time'], format=date_time_format))
    win_f_df = win_f_df.sort_values(by='time', ignore_index=True)
    median_f_df.insert(0, 'time', pd.to_datetime(median_f_df['comp_time'], format=date_time_format))
    median_f_df = median_f_df.sort_values(by='time', ignore_index=True)
    sipm_df.insert(0, 'time', pd.to_datetime(sipm_df['comp_time'], format=date_time_format))
    sipm_df = sipm_df.sort_values(by='time', ignore_index=True)
    return win_f_df, median_f_df, sipm_df


def get_data_dirs(dir_list: str, sub_folder: str = None) -> (pd.DataFrame, pd.DataFrame, pd.DataFrame):
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
        win_f, median_f, sipm = get_data_dir(os.path.join(directory, sub_folder))
        if i == 0:
            win_f_df = win_f
            median_f_df = median_f
            sipm_df = sipm
        else:
            win_f_df = pd.concat([win_f_df, win_f])
            median_f_df = pd.concat([median_f_df, median_f])
            sipm_df = pd.concat([sipm_df, sipm])
    return win_f_df, median_f_df, sipm_df


print(f"Muon data collection and anomaly detection V{VERSION}")

with open("config.json") as json_data_file:
    config = json.load(json_data_file)

# select folder(s) to be accessed for event data
root_dir = os.path.expanduser(config['event_files']['root_dir'])
# set single folder name here or leave empty for all folders to be accessed under root directory
single_dir_name = ""
directory_list = [os.path.join(root_dir, single_dir_name)]
# all folders
if not single_dir_name:
    directory_list = [os.path.join(root_dir, name) for name in os.listdir(root_dir) if
                      os.path.isdir(os.path.join(root_dir, name))]

# set up for plotting
fig, (ax1, ax2) = plt.subplots(nrows=2, sharex=True)

# all event plotting
ax1_2 = ax1.twinx()
ax1.set_xlabel('Date/Time (UTC)')
ax1.set_ylabel('Window Freq (Hz)')
ax1_2.set_ylabel('SIPM (mV)')
win_f_df, median_f_d, sipm = get_data_dirs(directory_list, "all")
ax1.plot(win_f_df['time'].values, win_f_df['win_f'].values, '-', color='silver')
ax1.plot(win_f_df['time'].values, win_f_df['median_f'].values, '+', color='gray')
ax1_2.plot(sipm['time'].values, sipm['sipm'].values, '.', color='red', markersize=3, alpha=0.3)
ax1.grid()
ax1.set_title("All Buffers", fontsize=10)

# anomaly plotting
ax2_2 = ax2.twinx()
ax2_2.set_ylabel('SIPM (mV)')

# anomaly event plotting
ax2.set_xlabel('Date/Time (UTC)')
ax2.set_ylabel('Window Freq (Hz)')
win_f_df, median_f_d, sipm = get_data_dirs(directory_list, "anomaly")
ax2.plot(win_f_df['time'].values, win_f_df['win_f'].values, '-', color='silver')
ax2_2.plot(sipm['time'].values, sipm['sipm'].values, '.', color='red', markersize=3, alpha=0.3)
ax2.grid()
ax2.set_title("Anomaly Buffers", fontsize=10)

plt.tight_layout()
plt.gcf().autofmt_xdate()
plt.show()



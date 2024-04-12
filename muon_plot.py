import os.path
import pandas as pd
import json
from os import listdir
from os.path import join
import matplotlib.pyplot as plt

date_time_format: str = "%Y%m%d %H%M%S.%f"


def get_data(directory) -> (pd.DataFrame, pd.DataFrame):
    """
    Get all event data from the specified directory.
    :param directory: Root directly holding the event data.
    :return:
    """
    file_list = [file for file in listdir(directory) if file.endswith('csv')]

    start_indices = []
    for i, file in enumerate(file_list):
        print(file)
        df = pd.read_csv(join(directory, file))
        # extract frequency rows
        if i == 0:
            win_f_df = df.loc[df['win_f'].notna()]
            median_f_df = df.loc[df['median_f'].notna()]
        else:
            win_f_df = pd.concat([win_f_df, df.loc[df['win_f'].notna()]], ignore_index=True)
            median_f_df = pd.concat([median_f_df, df.loc[df['median_f'].notna()]], ignore_index=True)

    win_f_df.insert(0, 'time', pd.to_datetime(win_f_df['comp_time'], format=date_time_format))
    win_f_df = win_f_df.sort_values(by='time', ignore_index=True)

    median_f_df.insert(0, 'time', pd.to_datetime(median_f_df['comp_time'], format=date_time_format))
    median_f_df = median_f_df.sort_values(by='time', ignore_index=True)

    return win_f_df, median_f_df


with open("config.json") as json_data_file:
    config = json.load(json_data_file)

root_dir = os.path.expanduser(config['event_files']['root_dir'])
root_dir = os.path.join(root_dir, "240411_183012")
fig, (ax1, ax2) = plt.subplots(nrows=2, sharex=True)


win_f_df, median_f_df = get_data(os.path.join(root_dir, "all"))
ax1.plot(win_f_df['time'].values, win_f_df['win_f'].values, 'g-')
ax1.plot(win_f_df['time'].values, win_f_df['median_f'].values, 'r+')

ax1.grid()

if os.path.exists(os.path.join(root_dir, "anomaly")):
    win_f_df, median_f_df = get_data(os.path.join(root_dir, "anomaly"))
    ax2.plot(win_f_df['time'].values, win_f_df['win_f'].values, 'g-')
    #ax2.plot(start_times, [0]*len(start_times), 'go')
    ax2.grid()

plt.tight_layout()
plt.gcf().autofmt_xdate()
plt.show()
a=1


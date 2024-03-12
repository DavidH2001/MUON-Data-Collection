import numpy as np
import pandas as pd
from os import listdir
from os.path import isfile, join
from datetime import datetime
import matplotlib.pyplot as plt

directory = 'C:/Users/dave/Temp/muon_data'
#df = pd.read_csv(log_file, names=['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'])
#a=1

date_time_format: str = "%Y-%m-%d %H:%M:%S.%f"


def plot_data(file):
    a=1
    # # Loop the data lines
    # with open(file, 'r') as temp_f:
    #     # Read the lines
    #     lines = temp_f.readlines()
    #
    #     for line in lines:
    #         fields = line.split(sep=',')
    #         if fields[1].strip() == "INFO":
    #             info_fields = fields[2].split()
    #             if info_fields[0].strip() == "window_time(s)":
    #                 a=1


file_list = [file for file in listdir(directory) if file.endswith('csv')]
win_f_df = None

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

#date_array = win_f_df['comp_time']
win_f_df['time'] = pd.to_datetime(win_f_df['comp_time'], format=date_time_format)
median_f_df['time'] = pd.to_datetime(median_f_df['comp_time'], format=date_time_format)

#price_array = win_f_df['win_f']
plt.plot(win_f_df['time'], win_f_df['win_f'], 'g-')
#plt.plot(median_f_df['time'], win_f_df['median_f'], linestyle='solid')
plt.plot(win_f_df['time'], win_f_df['median_f'], 'r+')

plt.gcf().autofmt_xdate()
plt.grid()
plt.show()
a=1


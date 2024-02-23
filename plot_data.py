import numpy as np
import pandas as pd
from os import listdir
from os.path import isfile, join
directory = 'C:/Users/dave/Temp/'
#df = pd.read_csv(log_file, names=['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'])
#a=1


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
for file in file_list:
    df = pd.read_csv(join(directory, file))
    # extract frequency rows
    f_df = df.loc[df['win_f'].notna()]
    a=1

plot_data(join(directory, file_list[0]))


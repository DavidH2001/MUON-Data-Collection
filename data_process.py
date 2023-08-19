#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jul 25 14:30:37 2022

@author: dave
"""

import pandas as pd
from collections import Counter
from matplotlib import pyplot as plt
import matplotlib.rcsetup as rcsetup

print(rcsetup.all_backends)


fname = '/home/dave/data_old.txt'

df = pd.read_csv(fname, sep=' ', header=None)
df['min'] = (df.iloc[:, 3] - df.iloc[0, 3]) / 60000
df = df.astype({'min': int}) 
counts = Counter(df['min'])
plt.plot(list(counts.keys()), list(counts.values()))
plt.grid()
plt.show()
a=1
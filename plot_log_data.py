import pandas as pd
log_file = 'C:/Users/dave/Temp/muon_log.txt'
#df = pd.read_csv(log_file, names=['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'])
#a=1
# Loop the data lines
with open(log_file, 'r') as temp_f:
    # Read the lines
    lines = temp_f.readlines()

    for line in lines:
        fields = line.split(sep=',')
        if fields[1].strip() == "INFO":
            info_fields = fields[2].split()
            if info_fields[0].strip() == "window_time(s)":
                a=1

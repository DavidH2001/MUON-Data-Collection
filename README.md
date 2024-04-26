# MUON Project

The software provided here is for use with the [CosmicWatch](https://github.com/spenceraxani/CosmicWatch-Desktop-Muon-Detector-v2?tab=readme-ov-file) Muon detectors. Its purpose is to collect event data 
from pairs of Muon detectors running in coincidence (master M and slave S) mode. The ultimate aim is to collect data 
from multiple sites to perform correlative analyses. 

## Software Description
The detection software connects to the serial interface of the S-detector after some initial user interaction. It then
monitors text lines, sent from the detector, looking for a valid event sequence. Note that the S-detector must be 
running the standard Arduino code as described [here](https://github.com/spenceraxani/CosmicWatch-Desktop-Muon-Detector-v2).
When a valid event line is received the detection sequence will begin and continue to do so until the system detects  
a Ctrl-C signal or the system is rebooted. The detector activity can be monitored via the command line used to start it 
or via browsing a log file written to a specified root directory. During runtime, all events are saved to a buffer 
along with separate frequency information that is calculated using a sliding window across the buffer. The detection of 
anomalies starts when the event buffer has been initially filled. This involves comparing the current central buffer 
event frequency to the current buffer median (Muon base level) frequency. The correspondence given via the 
[UKRAA](https://www.ukraa.com/) provides evidence that the Muon rates can vary between detectors. This could be explained 
for a number of reasons e.g., how the detectors were constructed, a variation in the components used, detector location, 
etc. The dynamic base level comparison used by the detection software will help compensate for any drift in the detector 
sensitivity. When a high (or low) central event frequency is detected the current buffer is saved to a file. Monitoring 
the central frequency means that we can obtain the sequence of events before and after a detected anomaly. In addition, 
the software may be configured to save all buffers independent of any occurring anomalies. The software also supplies 
the option to copy anomaly files to a remote FTP server. 

## Prerequisites

This software has been tested with Python 3.8 and 3.9. Other 3.x version may also work. The following additional 
packages are required to be included as part of your Python installation:

[ftplib](https://docs.python.org/3/library/ftplib.html#module-ftplib)<br/>
[pandas](https://pypi.org/project/pandas/)<br/>
[pyserial](https://pypi.org/project/pyserial/0)<br/>
[signal](https://docs.python.org/3/library/signal.html)

## Installation

Click on the *Code* button found at the top of this main GitHub project page and select *Download Zip*. Unzip
the download into a chosen directory of your computer. Alternatively, you can copy the project's URL and *git clone* the 
software directly from the repository. This way you will be able to obtain any updates quickly and make contributions to 
the code via a *Pull Request*. 

### Software configuration
Before you can run the software you will need to set up a number of parameters in the configuration file.
When you install the code you will find a template file in the project folder called *config.template.json*. Copy and 
rename this file to *config.json* in the sme directory. Open the copied file and set the following parameters as 
required:

* "user name" - designated unique name for logging event data and connecting to remote file server.
* "user password" - designated password name for connecting to remote file server. Optional, can be left blank.
* "user latitude" - float value representing the latitude of the user's detectors in degrees and decimal minutes. 
* "user longitude" - float value representing the longitude of the user's detectors in degrees and decimal minutes.
* "event_files root_dir" - string defining an existing directory where your event files will be saved locally. you must create this directory.
* "event_files save_all" - set to true* (default) if wanting to save all event buffers to files. 
* "system buff_size" - size of event buffer. Leave set to default."
* "system window_size" - size of frequency window. Leave set to default.
* "system anomaly_threshold" - threshold used to trigger an event anomaly. Leave set to default.
* "system logging_level" - set to "DEBUG" to log all activity or "INFO" to just log a summary.
* "system max_median_frequency" - set to maximum median frequency allowed. Leave set to default.   
* "remote ip_address" - IP address of remote file server. If this is left as an empty string then remote access will not be attempted.

Example config.json file:

```
{
    "user": {
        "name": "Dave",
        "password": "",
        "latitude": 50.81,
        "longitude": -1.22
    },
    "event_files": {
        "root_dir": "~/muon_data",
        "save_all": true
    },
    "system": {
        "buff_size": 210,
        "window_size": 10,
        "anomaly_threshold": 4.0,
        "logging_level": "INFO",
        "max_median_frequency": 1.0
    },
    "remote": {
        "ip_address": ""
    }
}
```

## Hardware configuration
Set up two detectors to run in coincidence mode making sure the intended S-detector is connected to the computer via a 
USB/serial cable. The image below shows M (top) and S (bottom) detectors running in coincidence mode. The S-detector is 
connected to a Raspberry Pi which is running the detection software. 

![](/doc/image_setup.jpg)

## Running the software

1) Start the detection software on the logging computer. For example:
```
$ python muon_run.py
```
or, if using a virtual environment:
```
$ ./venv/Scripts/activate
$ python muon_run.py
```
Alternatively, you may wish to run the software directly from an IDE editor such as *PyCharm* or *Thonny*.

On start-up you will be presented with some information and a prompt to connect with the S-detector: 
```commandline
>python muon_run.py
Muon data collection and anomaly detection V0.2.0
user_id=Dave_50_81_-1_22
buff_size=210, window_size=10, anomaly_threshold=4.0
Creating directory C:\Users\dave/muon_data\240426_132622
Host platform: win32
Connect the S-detector to a serial port on the host.
Select [return] to continue or [Q] to quit:
```

Check that the information is correct e.g., *user_id*, *buff_size*, etc. Also make ensure that your computer is connected
to the S-detectors seral port. When ready press *return* to continue or *Q* to quit:

```commandline
Available serial ports:
[1] COM4
[Q] Quit
Identify which serial port is connected to the S detector or Q to quit:
```
From the supplied list of available serial ports supported on your computer, select the one attached to the S-detector.
Note the process of listing the ports will make the connected detector re-boot:

```commandline
COM4 selected
Reset the M-detector and then the S-detector.
Select [return] to continue or [Q] to quit:
```
Now reset your detectors so as they are running in coincidence mode. Make sure the detector connected to your computer
shows itself as the S-detector and the other as the M-detector. When ready press *return* to continue. Try to do this
as soon as S-detector runs to avoid spurious events. 

### Directories and Logging
Each time the software starts it will create a new session directory based on the local data and time under the root 
directory defined in the configuration. All event files as well as an activity log relating to the session will be 
written here. Event anomaly buffers will be saved automatically to a subdirectory called *anomaly*. And, likewise, if 
you have configured to save all event buffers then these will be saved in subdirectory called *all*.  

A log of activity is maintained each time the software is run. The log is streamed live through the launching console as 
well as saved to a file called *muon_log.txt* which is created automatically in the current session directory. Viewing
this log is the best way to determine your setup is working correctly. Events should normally be received at a rate well 
below 1Hz otherwise you may not be running in coincidence mode or something cosmologically strange is occurring! 

If your configuration logging level is set to *DEBUG* then you will be able to log all events as well as other 
information.  

Example log:
```commandline
2024-04-24:11:43:44, INFO, Running detection software V0.2.0 using DEBUG logging level
2024-04-24:11:43:44, INFO, buff_size=210, window_size=10, anomaly_threshold=2.5
2024-04-24:11:43:44, INFO, latitude=10.0, longitude=10.0
2024-04-24:11:43:44, INFO, Acquisition thread started
2024-04-24:11:43:44, INFO, Waiting for S-detector initial event line...
2024-04-24:11:43:53, INFO, Event line detected - beginning acquisition
2024-04-24:11:43:53, INFO, Note, only first 3 events will be displayed if logging at INFO level...
2024-04-24:11:43:53, INFO, ['20240424 104353.764', 1, 4281, 335, 61.77, 1106, 18.54, nan, nan]
2024-04-24:11:44:23, INFO, ['20240424 104423.738', 2, 34258, 387, 81.05, 6624, 18.75, nan, nan]
2024-04-24:11:44:25, INFO, ['20240424 104425.140', 3, 35661, 364, 71.71, 6812, 18.0, nan, nan]
2024-04-24:11:44:26, DEBUG, ['20240424 104426.295', 4, 36815, 492, 134.92, 7000, 18.0, nan, nan]
2024-04-24:11:44:30, DEBUG, ['20240424 104430.365', 5, 40887, 511, 149.39, 7748, 18.0, nan, nan]
2024-04-24:11:44:31, DEBUG, ['20240424 104431.784', 6, 42307, 387, 81.05, 8124, 18.54, nan, nan]
```

## Accessing remote FTP server
To enable your anomaly files to be copied to a remote FTP server you will need to update your configuration to include
a valid *name*, *password* and *ip_address*. It aso important to make sure you have set the *latitude* and *longitude* 
correctly for your detectors as these will be used to create a personal directory on the FTP server for your files.

```commandline
{
    "user": {
        "name": "Dave",
        "password": "TheSeverPassword",
        "latitude": 50.81,
        "longitude": -1.22
    },
    "event_files": {
        "root_dir": "~/muon_data",
        "save_all": true
    },
    "system": {
        "buff_size": 210,
        "window_size": 10,
        "anomaly_threshold": 4.0,
        "logging_level": "INFO",
        "max_median_frequency": 1.0
    },
    "remote": {
        "ip_address": "111.222.333.444"
    }
}
```

Once you have configured the above items the software will attempt to connect with the remote FTP server on start-up. 
Here the instructions will show some additional information. For example:
```commandline
Muon data collection and anomaly detection V0.2.0
user_id=Dave_50_81_-1_22
buff_size=210, window_size=10, anomaly_threshold=4.0
Creating directory C:\Users\dave/muon_data\240426_145706
Checking FTP connection for user folder Dave_50_81_-1_22
Waiting for response from 111.222.333.444...
Welcome!
Remote user directory found.
Select [return] to continue or [Q] to quit:
```
If this fails to show a successful connection then make sure the IP address is set correctly. You will still be able to 
proceed as the software will retry to connect later. If you simply want to test your connection then start the software 
and choose to quit rather than continue with event acquisition.    


### Testing remote access
EXAMPLE HERE

## Examining results and plotting

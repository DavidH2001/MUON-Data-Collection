# MUON Project

Data collection software for use with the [CosmicWatch](https://github.com/spenceraxani/CosmicWatch-Desktop-Muon-Detector-v2?tab=readme-ov-file) 
Muon detectors.

## Prerequisites

This software has been tested with Python 3.8 and 3.9. Other 3.x version may also work. The following additional 
packages are required to be included as part of your Python installation:

[ftplib](https://docs.python.org/3/library/ftplib.html#module-ftplib)<br/>
[pandas](https://pypi.org/project/pandas/)<br/>
[pyserial](https://pypi.org/project/pyserial/0)<br/>
[signal](https://docs.python.org/3/library/signal.html)

## Installation

Click on the *Code* button found at the top of the main GitHub project page and select *Download Zip*. Unzip
the download into a chosen directory of your computer. Alternatively, you can copy the project's URL and clone the 
software directly from the repository. This way you will be able to obtain any updates quickly and make changes to the 
code via a *Pull Request*. 

### Software configuration
Before you can run the data collector you will need to set up a number of parameters in the configuration file.
When you install the code you will find a template file in the project folder called *config.template.json*. Copy and 
rename this file to *config.json* in the sme directory. Open the copied file and set the following parameters:

* "user name" - designated unique name for logging event data and connecting to remote file server.
* "user password" - designated password name for connecting to remote file server. Can be left blank.
* "user latitude" - float value representing the latitude of the user's detectors in degrees and decimal minutes. 
* "user longitude" - float value representing the longitude of the user's detectors in degrees and decimal minutes.
* "event_files root_dir" - string defining an existing directory where your event files will be saved locally.
* "system buff_size" - size of event buffer. Leave set to default.
* "system window_size" - size of frequency window. Leave set to default.
* "system anomaly_threshold" - threshold used to trigger an event anomaly. Leave set to default.
* "system logging_level" - set to "DEBUG" to log all messages or "INFO" to just log a summary.
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
        "root_dir": "~/muon_data"
    },
    "system": {
        "buff_size": 210,
        "window_size": 10,
        "anomaly_threshold": 4.0,
        "logging_level": "DEBUG",
        "max_median_frequency": 1.0
    },
    "remote": {
        "ip_address": ""
    }
}
```

### Hardware configuration
Set up two detectors to run in coincidence mode making sure the intended S (slave) detector is connected to the logging
computer via a USB cable. The image below shows M (top) and S (bottom) detectors running in coincidence mode. The S 
detector is connected to a Raspberry Pi which is running the detection software. 

![](/doc/image_setup.jpg)

### Running data acquisition and logging

Follow this sequence to start acquiring events:

1) Start the detection software on the logging computer. For example:
```
$ python muon_run.py
```
or, if using a virtual environment:
```
$ ./venv/Scripts/activate
$ python muon_run.py
```

If you have configured an IP address then the collector will attempt to connect with the remote file server. If this
fails to connect then make sure the IP address is set correctly. You will still be able to proceed with start-up as the 
software will retry to connect later.       

When running ... a log file will be created and written to throughout 
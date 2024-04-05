# MUON Project

Data collection software for use with the [CosmicWatch](https://github.com/spenceraxani/CosmicWatch-Desktop-Muon-Detector-v2?tab=readme-ov-file) 
Muon detectors.

## Prerequisites

This software has been tested with Python 3.8 and 3.9. Earlier 3.x version may also work. The following packages are 
required to be included as part of your Python instance:

[pandas](https://pypi.org/project/pandas/)<br/>
[pyserial](https://pypi.org/project/pyserial/0)


## Installation

Click on the *Code* button found at the top of the main GitHub project page and select *Download Zip*. Unzip
the download into a chosen directory of your computer. Alternatively, you can copy the project's URL and clone the 
software directly from the repository. This way you will be able to obtain any updates quickly and make changes to the 
code via a *Pull Request*. 


### Software Configuration
Before you can run the data collector you will need to set up a number of parameters in the configuration file.
When you install the code you will find a template file in the project folder called *config.template.json*. Copy and 
rename this file. Open the copied file and set the following parameters:

* "user name" - designated unique name for logging event data and connecting to remote file server.
* "user password" - designated password name for connecting to remote file server.
* "user latitude" - float value representing the latitude of the user's detectors.
* "user longitude" - float value representing the longitude of the user's detectors.
* "event_files root_dir" - string defining an existing directory where your event files will be saved.
* "remote ip_address" - IP address of remote file server. If this is left as an empty string then remote access will not be attempted.

### Hardware Configuration
Set up two detectors to run in coincidence mode making sure the intended S (slave) detector is connected to the logging
computer via a USB cable.

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
fails to connect then make sure the IP address is correct. You will still be able to proceed with start-up as the 
collection software will retry to connect later.       


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
the download into a chosen directory of your computer.

Alternatively, you can copy the project's URL and clone the software directly from the repository. This way you will 
be able to obtain any updates quickly and make changes to the code via a *Pull Request*. 

## Running

### Configuration
Before you can run the data collector you will need to set up a number of parameters in the configuration file 
*config.json* found in the project folder:
* "user latitude" - float value representing the latitude of the user detectors.
* "user longitude" - float value representing the longitude of the user detectors.
* "event_files root_dir" - string defining an existing directory where your event files will be saved.

### Execution

```
> python muon_run.py
```


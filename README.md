# 1. Intermediate Server
Welcome to the intermediate server repository. The intermediate server is a black-box application server which sits between the SUFST car telemetry system and the front-end GUI clients for the translation of telemetry frames. Moreover, the telemetry communciation protocol is defined here in which the car telemetry system and front-end GUI must adhere to. 

# 2. Wiki
Please read the wiki @https://github.com/sufst/intermediate-server/wiki

# 3. Building & Running
This project is built using Python 3, the Digi-Xbee Framework for integration between the XBee on the Car, as well as Dash Plotly for the front-end GUI Emulator. 

#### Installing Dependencies: 

1. Clone the repo.
1. Make sure Python is installed in your machine. 

To check run `python --version`. Note that  Python 3.x is required. If Python is not installed, download and install Python 3.x from [here](https://www.python.org/)

3. Make sure `pip` is installed. 

It should be if Python is already installed - check its version with `pip --version`. Please note that on macOS you might need to run `pip3 --version`. 

4. Run `pip install -r requirements.txt` from the root of the repository. 

For macOS installations in case the above doesn't work use `pip3 install -r requirements.txt`

#### Quick Start Run

1. Run the file you want using `python3 <filename>.py` or `python <filename>.py` depending on your OS and python installation. 
2. Each of the files (main.py, car_emlator.py, and gui_emulator.py) take command line arguments, but if no command line arguments are passed then default values are used which will get the files up and running and will operate together.
 

Please note that currently (December 29th 2020) there is a bug that doesn't let all the digi-xbee dependencies to compile properly. This is known to the developers and a workaround solution is mentioned in this repo's wiki [here](https://github.com/sufst/intermediate-server/wiki)

# 4. Contributions :heart:
Any contributions are welcomed. Please check the issues page for outstanding feature requests or bugs. If you contribute to resolve an issue please submit a pull request for your contribution and it will be reviewed.

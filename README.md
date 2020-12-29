# 1. Intermediate Server
Welcome to the intermediate server repository. The intermediate server is a black-box application server which sits between the SUFST car telemetry system and the front-end GUI clients for the translation of telemetry frames. Moreover, the telemetry communciation protocol is defined here in which the car telemetry system and front-end GUI must adhere to. 

# 2. Wiki
Please read the wiki @https://github.com/sufst/intermediate-server/wiki

# 3. Building & Running
This project is built using Python 3. 

#### Installing Dependencies: 

1. Clone the repo.
1. Make sure Python is installed in your machine. To check run `python --version`. Note that  Python 3.x is required. If Python is not installed, download and install Python 3.x from [here](https://www.python.org/)
1. Make sure `pip` is installed - it should be if Python is already installed - check its version with `pip --version`. Please note that on macOS you might need to run `pip3 --version`. 
1. Compile the requirements.sh file using `chmod +x requirements.sh`
1. Run the .sh file using `./requirements.sh`
1. If the .sh file didn't work please open the file and run the lines from the .sh file to your terminal one by one. (Note for macOS with pip3 you must replace all `pip` instances from requirements.sh with `pip3`). 

#### Running Source Files: 

1. Run the file you want using `python3 <filename>.py` or `python <filename>.py` depending on your OS and python installation. 

# 4. Contributions :heart:
Any contributions are welcomed. Please check the issues page for outstanding feature requests or bugs. If you contribute to resolve an issue please submit a pull request for your contribution and it will be reviewed.

# Intermediate Server
Welcome to the intermediate server repository. The intermediate server is a black-box intermediate server that sits between the SUFST car telemetry system and the back-end server to translate PDU frames to sensors. 

Relevant Repositories are linked below:
- [On-Car-Telemetry](https://github.com/sufst/on-car-telemetry) - Embedded Code for On-Car-Telemetry Module
- [Back-end Server](https://github.com/sufst/back-end) - SUFST Back-end server. 
- [can-defs](https://github.com/sufst/can-defs/) - Helper module to generate `schema.json`, `sensors.json` files and embedded C code. 

## Getting Started 
To install the server, follow the instructions below: 

### 1. Prerequisites

Currently, you will need the following items installed on your system in order to get the server running: 
- `Git`  
- `Python3.9` 

You also need a **UNIX based environment**. If you're using a macOS or Linux system, you're fine. If you're using Windows, you need to either install *WSL*. 

*Note: Currently, only Python versions 3.9.x work. If you have anything higher, make sure to install a supported version.*

### 2. Installing & Building

1. Clone the repository using: 

```
https://github.com/sufst/intermediate-server.git
```

2. Open the terminal window and navigate to the folder where the server was cloned. 

*Note: On Windows, this need to be a WSL terminal.*

3. Create a new Python Virtual Environment named `venv` using: 

```
python3 -m venv venv
```

*Note: If you have multiple versions of Python3 installed, you will need to replace `python3` with `python3.9`*.

4. Activate the Python Virtual Environment using:

```
source venv/bin/activate
```

`(venv)` should now appear in the LHS of your terminal.

5. Install all dependancies using: 

```
pip install wheel 
```

and then 

```
pip install -r requirements.txt
```

If everything installs fine, you should now be able to run the server using 

```
python server.py
```

You can cancel the server anything with `Control+C`. To leave/exit the python venv run `deactivate`. 

## Running 
Once the server is installed, you can run it anytime using the following steps. 

1. Open a terminal window and navigate to the intermediate-server folder. 

*Note: On Windows, this need to be a WSL terminal.*

2. Activate the Python Virtual Environment using:

```
source venv/bin/activate
```

`(venv)` should now appear in the LHS of your terminal.

3. Run the python file to start the server using: 

```
python server.py 
```

You can cancel the server anything with `Control+C`. To leave/exit the python venv run `deactivate`. 

## Known Issues: 

1. Currently, the `schema.json` and `verson.json` files need to be **manually** updated everytime a new version of these is generated from the [can-defs](https://github.com/sufst/can-defs/) repo. In the future this will be automatically handled using `git-submodules`. 

## Contact - Maintenance
For any questions, please contact [Andreas](https://github.com/AndreasDemenagas). Note, this server was originally developed by [Nathan](https://github.com/Nathanrs97).



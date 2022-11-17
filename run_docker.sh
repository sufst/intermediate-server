#!/bin/bash

#
# Bash script to build docker image and launch container.
# author: AndreasDemenagas (@AndreasDemenagas)
# date: October 27th 2022
#
# Copyright (C) 2022 SUFST
#

env -i

source venv/bin/activate

# Maybe not doe this for now. Let's use the requirements file to
# pip freeze > requirements.txt
deactivate

docker build -t sufst-intermediate-server .
docker stop sufst-intermediate-server
docker rm sufst-intermediate-server

# Assigns localhost to host.docker.internal (host.docker.internal = the localhost of the host machine)
# host-gateway = alias to my localhost
docker run --env-file docker.env --add-host host.docker.internal:host-gateway -it --rm --name sufst-intermediate-server sufst-intermediate-server

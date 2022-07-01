# Pulling Intermediate Server. 

echo 'Updating Intermediate Server...'

QUITE=$1

if [ $QUITE = '-q' ]
then
    git pull -q
else
   git pull 
fi

source inter-server-venv/bin/activate

python server.py
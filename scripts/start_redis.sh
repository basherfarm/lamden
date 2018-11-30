# Find a free port to use
port=$(python3 ./scripts/free_port.py)
pw=$(python3 ./scripts/random_password.py)

if [[ "$CIRCLECI" == "true" ]]
then
    chmod 777 ./venv/bin/activate
    ./venv/bin/activate
fi

# Configure env files
export PYTHONPATH=$(pwd)
export REDIS_PORT=$port
export REDIS_PASSWORD=$pw

echo "
REDIS_PORT=$REDIS_PORT
REDIS_PASSWORD=$REDIS_PASSWORD
" > docker/redis.env

echo "Starting Redis server..."
redis-server

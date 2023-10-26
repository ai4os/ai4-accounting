# Take a snapshot of the Nomad cluster.
# Make sure to properly adapt the paths to the Nomad certs
#
# This script must run every 6 hours as a cronjob:
# 0 */4 * * * /bin/bash /mnt/ai4-logs/ai4-accounting/take_snapshot.sh

# Export proper Nomad variables
export NOMAD_ADDR=https://193.146.75.221:4646  # production cluster
export NOMAD_CACERT=/home/ubuntu/nomad-certs/nomad-prod/nomad-ca.pem
export NOMAD_CLIENT_CERT=/home/ubuntu/nomad-certs/nomad-prod/cli.pem
export NOMAD_CLIENT_KEY=/home/ubuntu/nomad-certs/nomad-prod/cli-key.pem
export NOMAD_TLS_SERVER_NAME=server.global.nomad

# Move to main directory (where this script is located)
cd $(dirname "$0")

#TODO: make git pull?

# Run .py script
source ./myenv/bin/activate
python3 take_snapshot.py
python3 summarize.py
deactivate

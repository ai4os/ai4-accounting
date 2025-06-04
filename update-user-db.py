"""
Add users to a database.
"""

import json
from pathlib import Path

import nomad
import pandas as pd

# Disable insecure requests warning
import warnings
warnings.filterwarnings("ignore")


print("Updating users database")

user_dir = Path(__file__).resolve().parent / 'users'
json_pth = user_dir / "user-db.json"
csv_pth = user_dir / "user-db.csv"

# Load existing database or create one from scratch
keys = ['name', 'email']
if json_pth.exists():
    with open(json_pth, 'r') as f:
        users = json.load(f)
else:
    users = {}

# Parse current deployments and add new users
Nomad = nomad.Nomad()
namespaces = ['ai4eosc', 'imagine', 'ai4life']
snapshot = {k: [] for k in namespaces}
for namespace in namespaces:

    print(f"  Processing {namespace} ...")

    jobs = Nomad.jobs.get_jobs(namespace=namespace)  # job summaries
    for j in jobs:

        # Skip jobs that are not modules or tools
        # (useful for admins who might have deployed other jobs eg. Traefik)
        if not (j['Name'].startswith('module-') or j['Name'].startswith('tool-')):
            print(f"Ignoring {j['Name']}")
            continue

        try:
            j = Nomad.job.get_job(
                id_=j['ID'],
                namespace=namespace,
            )

            # Overwrite user info in database
            id_ = j['Meta']['owner']
            user = users.get(id_, {})
            for k in keys:
                if (f'owner_{k}' in j['Meta']):
                    user[k] = j['Meta'][f'owner_{k}']
            users[id_] = user

        except Exception:
            print(f"   Failed to retrieve {j['ID']}")

# Save new database to JSON
with open(json_pth, 'w') as f:
    json.dump(users, f)

# Save to CSV for better reading
df = pd.DataFrame.from_dict(users).T
df.index = df.index.set_names(['user id'])
df.to_csv(csv_pth, sep=';')

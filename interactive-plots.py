"""
Interactive plot of stats usage.
"""

from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path

import rich
import typer


snapshot_dir = Path(__file__).resolve().parent / 'snapshots'


# def main(
#     ini_date: str,
#     end_date: str,
#     ):

from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
from string import Template

import plotly.express as px


import typer


main_dir = Path.cwd()
snapshot_dir =  main_dir / 'snapshots'
html_dir = Path(__file__).resolve().parent / 'htmls'
# html_dir = main_dir / 'htmls'

# def main(
#     ini_date: str,
#     end_date: str,
#     ):

namespaces = ['ai4eosc', 'imagine']
stats = {k: {} for k in namespaces}
stats['dates'] = []
resources = [
    'cpu_num',
    'cpu_MHz',
    'memory_MB',
    'disk_MB',
    'gpu_num',
]
for k in namespaces:
    stats[k] = {
        'jobs_running': [],
        'jobs_queued': [],
    }
    for r in resources:
        stats[k][r] = []

# # Transform to datetimes
# ini_dt = datetime.strptime(ini_date,'%Y-%m-%d')
# end_dt = datetime.strptime(end_date,'%Y-%m-%d')

for snapshot_pth in sorted(snapshot_dir.glob('**/*.json')):
# for snapshot_pth in sorted(snapshot_dir.glob('**/*.json'))[-2:-1]:

    snapshot_dt = datetime.strptime(snapshot_pth.stem, '%Y-%m-%dT%H:%M:%S')

    # # Skip files outside the date range
    # if not (ini_dt <= snapshot_dt <= end_dt):
    #     continue

    # Load the snapshot
    with open(snapshot_pth, 'r') as f:
        snapshot = json.load(f)

    stats['dates'].append(snapshot_pth.stem)
    for namespace in namespaces:

        tmp = {k: 0 for k in stats[namespace].keys()}

        for job in snapshot[namespace]:

            # Ignore queued jobs, error jobs, etc
            if job['status'] not in ['running', 'queued']:
                continue

            # Aggregate status
            tmp[f"jobs_{job['status']}"] += 1

            if job['status'] == 'running':

                # Older jobs where misconfigured (cpuMHz was set instead of cpu_cores)
                #TODO: remove when old jobs no longer exist
                if job['resources']['cpu_num'] == 0:
                    job['resources']['cpu_num'] = job['resources']['cpu_MHz']

                # Aggregate resources
                for r in resources:
                    tmp[r] += job['resources'][r]

        # Append aggregation to stats
        for k in tmp.keys():
            stats[namespace][k].append(tmp[k])


# Generate plots
labels = {
    'cpu_num': 'CPU cores',
    'cpu_MHz': 'CPU frequency (MHz)',
    'memory_MB': 'RAM memory (MB)',
    'disk_MB': 'Disk memory (MB)',
    'gpu_num': ' Number of GPUs',
    'jobs_running': 'Jobs running',
    'jobs_queued': 'Jobs queued',
}

with open(html_dir / f'template.html', 'r') as f:
    html_template = Template(f.read())

for namespace in namespaces:

    with open(html_dir / f'{namespace}.html', 'w') as f:

        html = deepcopy(html_template)
        divs = {}
        for k in stats[namespace].keys():

            fig = px.area(
                x=stats['dates'],
                y=stats[namespace][k],
                title=labels[k],
                labels={
                    'x': 'Dates',
                    # 'y': labels[k],
                    'y': '',
                },
                width=800, height=400,
            )

            divs[k] = fig.to_html(full_html=False, include_plotlyjs='cdn')

        f.write(html.safe_substitute(divs))

# if __name__ == "__main__":
#     # typer.run(main)
#     main(
#         ini_date='2023-09-01',
#         end_date = '2023-09-10',
#     )


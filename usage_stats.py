"""
Get the accounting reports for a given period.
"""
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path

import rich
import typer


snapshot_dir = Path(__file__).resolve().parent / 'snapshots'


def main(
    ini_date: str,
    end_date: str,
    ):

    namespaces = ['ai4eosc', 'imagine']
    accounting ={k: {} for k in namespaces}

    # Transform to datetimes
    ini_dt = datetime.strptime(ini_date,'%Y-%m-%d')
    end_dt = datetime.strptime(end_date,'%Y-%m-%d')

    prev_snapshot_dt = deepcopy(ini_dt)  # datetime of last snapshot; starts at ini_date

    for snapshot_pth in sorted(snapshot_dir.glob('**/*.json')):

        snapshot_dt = datetime.strptime(snapshot_pth.stem, '%Y-%m-%dT%H:%M:%S')

        # Skip files outside the date range
        if not (ini_dt <= snapshot_dt <= end_dt):
            continue

        # Load the snapshot
        with open(snapshot_pth, 'r') as f:
            snapshot = json.load(f)

        for namespace in namespaces:
            for job in snapshot[namespace]:

                # Ignore queued jobs, error jobs, etc
                if job['status'] not in ['running', 'dead']:
                    continue

                # Ignore dead jobs that failed without ever been deployed
                if job['status'] == 'dead' and not job['alloc_start']:
                    continue

                # Ignore running jobs that do not have alloc start
                # Weird case, but can happen
                if job['status'] == 'running' and not job['alloc_start']:
                    print(f"{snapshot_dt} Ignoring running with no alloc start")
                    continue

                # Older jobs where misconfigured (cpuMHz was set instead of cpu_cores)
                #TODO: remove when old jobs no longer exist
                if job['resources']['cpu_num'] == 0:
                    job['resources']['cpu_num'] = job['resources']['cpu_MHz']

                # Compute most restrictive start time
                start = datetime.strptime(job['alloc_start'][:-4], '%Y-%m-%dT%H:%M:%S.%f')  # trim to microseconds
                start = max(prev_snapshot_dt, start)

                # Compute most restrictive end time
                if job['status'] == 'dead':
                    end = datetime.strptime(job['alloc_end'][:-4], '%Y-%m-%dT%H:%M:%S.%f')  # trim to microseconds
                    end = min(snapshot_dt, end)
                else:
                    end = snapshot_dt

                # Compute time delta
                # Ignore negative timedeltas (can happen if dead job is repeated from last snapshot)
                seconds = (end - start).total_seconds()
                seconds = max(0, seconds)

                # Add to overall accounting
                for k, v in job['resources'].items():
                    accounting[namespace][k] = accounting[namespace].get(k, 0) + v * seconds

        # Update snapshot time
        prev_snapshot_dt = snapshot_dt

    # Convert resource to resource/hr
    for namespace in namespaces:
        for k in accounting[namespace].copy().keys():
            accounting[namespace][f'{k}/hr'] = int(accounting[namespace].pop(k) / 3600)

    # Print pretty report
    console = rich.console.Console(record=True)

    for namespace in namespaces:

        table = rich.table.Table(
            title=f"{namespace.upper()} accounting for the period {ini_date}:{end_date}",
            show_header=False,
        )

        table.add_column("Resources", justify="right", style="cyan")
        table.add_column("", justify="right", style="pink1")

        for k, v in accounting[namespace].items():
            table.add_row(k, str(v))

        console.print(table, soft_wrap=True)
        # print(console.export_html())

    #TODO: remove when old jobs no longer exist
    console.print(
        "[orange1][b]Warning[not b][not orange1] cpu_MHz numbers might be unreliable due to old jobs " \
        "being misconfigured",
    )

if __name__ == "__main__":

    typer.run(main)
    
    # main(
    #     ini_date='2024-03-01',
    #     end_date = '2024-08-31',
    # )

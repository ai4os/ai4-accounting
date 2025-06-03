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
    ini_date: str = None,
    end_date: str = None,
    ):

    namespaces = ['ai4eosc', 'imagine', 'ai4life']
    accounting = {k: {} for k in namespaces}
    jobset = {k: set() for k in namespaces}  # keep track of number of jobs per namespace
    userset = {k: set() for k in namespaces}  # keep track of number of jobs per namespace

    snapshot_list = sorted(snapshot_dir.glob('**/*.json'))

    # Transform to datetimes
    # Use user values or else default to first/last snapshots
    ini_dt = datetime.strptime(ini_date,'%Y-%m-%d') if ini_date \
        else datetime.strptime(snapshot_list[0].stem, '%Y-%m-%dT%H:%M:%S')
    end_dt = datetime.strptime(end_date,'%Y-%m-%d') if end_date \
        else datetime.strptime(snapshot_list[-1].stem, '%Y-%m-%dT%H:%M:%S')
    end_dt = end_dt.replace(hour=23, minute=59, second=59)  # include end_dt in the range

    prev_snapshot_dt = deepcopy(ini_dt)  # datetime of last snapshot; starts at ini_date

    # Keep track of ignored misformated jobs
    ignored = set()

    for snapshot_pth in snapshot_list:

        snapshot_dt = datetime.strptime(snapshot_pth.stem, '%Y-%m-%dT%H:%M:%S')

        # Skip files outside the date range
        if not (ini_dt <= snapshot_dt <= end_dt):
            continue

        # Load the snapshot
        with open(snapshot_pth, 'r') as f:
            snapshot = json.load(f)

        for namespace in namespaces:
            for job in snapshot.get(namespace, []):

                # Ignore queued jobs, error jobs, etc
                if job['status'] not in ['running', 'dead']:
                    continue

                # Ignore dead jobs that failed without ever been deployed
                if job['status'] == 'dead' and not job['alloc_start']:
                    continue

                # Ignore dead jobs that are badly formatted
                # Weird case, but can happen
                if job['status'] == 'dead' and  not job['alloc_end']:
                    if job['job_ID'] not in ignored:
                        print(f"{snapshot_dt.date()} Ignoring: dead with no alloc end (ID: {job['job_ID']})")
                        ignored.add(job['job_ID'])
                    continue

                # Ignore running jobs that do not have alloc start
                # Weird case, but can happen
                if job['status'] == 'running' and not job['alloc_start']:
                    if job['job_ID'] not in ignored:
                        print(f"{snapshot_dt.date()} Ignoring: running with no alloc start (ID: {job['job_ID']})")
                        ignored.add(job['job_ID'])
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

                # Track job and user
                jobset[namespace].add(job['job_ID'])
                userset[namespace].add(job['owner'])

        # Update snapshot time
        prev_snapshot_dt = snapshot_dt

    # Convert from resource-seconds to resource-hour
    for namespace in namespaces:
        for k in accounting[namespace].copy().keys():
            accounting[namespace][f'{k} hours'] = int(accounting[namespace].pop(k) / 3600)

    # Print pretty report
    console = rich.console.Console(record=True)

    for namespace in namespaces:

        table = rich.table.Table(
            title=f"{namespace.upper()} accounting for the period {ini_dt.date()}:{end_dt.date()}",
            show_header=False,
        )

        table.add_column("Resources", justify="right", style="cyan")
        table.add_column("", justify="right", style="pink1")

        for k, v in accounting[namespace].items():
            table.add_row(k, str(v))

        table.add_row('Nº jobs', str(len(jobset[namespace])))
        table.add_row('Nº active users', str(len(userset[namespace])))

        console.print(table, soft_wrap=True)
        # print(console.export_html())

    # Show table for aggregate of all namespaces
    table = rich.table.Table(
        title=f"Aggregated accounting for the period {ini_dt.date()}:{end_dt.date()}",
        show_header=False,
    )
    table.add_column("Resources", justify="right", style="cyan")
    table.add_column("", justify="right", style="pink1")
    for res in list(accounting.values())[0].keys():
        v = sum([accounting[n][res] for n in namespaces])
        table.add_row(res, str(v))
    table.add_row('Nº jobs', str(sum([len(s) for s in jobset.values()])))
    table.add_row('Nº active users', str(len(set.union(*userset.values()))))
    console.print(table, soft_wrap=True)


if __name__ == "__main__":

    typer.run(main)

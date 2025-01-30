"""
Generate a summary of the logs:

* daily stats of the whole cluster and separated by namespaces
* aggregated stats per user/namespace
"""

from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path

import pandas as pd
import typer


main_dir = Path(__file__).resolve().parent
snapshot_dir =  main_dir / 'snapshots'
summary_dir = main_dir / 'summaries'
html_dir = main_dir / 'htmls'


def main(
    ini_date: str = None,
    end_date: str = None,
    ):

    snapshot_list = sorted(snapshot_dir.glob('**/*.json'))

    # Transform to datetimes
    # Use user values or else default to first/last snapshots
    ini_dt = datetime.strptime(ini_date,'%Y-%m-%d') if ini_date \
        else datetime.strptime(snapshot_list[0].stem, '%Y-%m-%dT%H:%M:%S')
    end_dt = datetime.strptime(end_date,'%Y-%m-%d') if end_date \
        else datetime.strptime(snapshot_list[-1].stem, '%Y-%m-%dT%H:%M:%S')
    end_dt = end_dt.replace(hour=23, minute=59, second=59)  # include end_dt in the range

    print(f"Summarizing logs for the period {ini_dt.date()}:{end_dt.date()} ...")

    # Create dict first for fast appending, then convert to Pandas Dataframe for easier
    # aggregation
    resources = [
        'cpu_num',
        'cpu_MHz',
        'memory_MB',
        'disk_MB',
        'gpu_num',
    ]
    others = [
        'date',
        'namespace',
        'owner',
        'status',
    ]
    df = {k: [] for k in others + resources}

    # Iterate over snapshots
    namespaces = ['ai4eosc', 'imagine', 'ai4life']
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
                if (job['status'] not in ['running', 'queued']):
                    continue

                # If job is running but has no `alloc_start` let's count it as queued
                if job['status'] == 'running' and not job.get('alloc_start'):
                    job['status'] = 'queued'

                # Add variables
                df['date'].append(snapshot_pth.stem)
                df['namespace'].append(namespace)
                df['status'].append(job['status'])
                df['owner'].append(job['owner'])

                if job['status'] == 'running':

                    # Older jobs where misconfigured (cpuMHz was set instead of cpu_cores)
                    #TODO: remove when old jobs no longer exist
                    if job['resources']['cpu_num'] == 0:
                        job['resources']['cpu_num'] = job['resources']['cpu_MHz']

                    # Aggregate resources
                    for r in resources:
                        df[r].append(job['resources'][r])

                elif job['status'] == 'queued':

                    # No resources
                    for r in resources:
                        df[r].append(None)

            # If the snapshot exists, but there were not jobs running/queued, resources
            # should be set to zero in order to not skip that timestamp in the time series
            # We should only skip the timestamp if the snapshot wasn't taken.
            if not snapshot.get(namespace, []):
                df['date'].append(snapshot_pth.stem)
                df['namespace'].append(namespace)
                df['status'].append(None)
                df['owner'].append(None)

                for r in resources:
                    df[r].append(0)

    # Convert to Dataframe
    df = pd.DataFrame.from_dict(df)
    df["date"] = pd.to_datetime(df["date"])

    ####################################################################################
    # Generate timeseries                                                              #
    ####################################################################################

    # Generate namespace time series
    stats_ns = df.groupby(['date', 'namespace']).sum()  # average jobs inside the same snapshot
    stats_ns = stats_ns.reset_index(level=0)  # move 'date' to column
    stats_ns['date'] = stats_ns['date'].dt.date  # remove hours
    stats_ns = stats_ns.groupby(['date', 'namespace']).mean()  # average hourly snapshots to daily average
    stats_ns = stats_ns.round(0).astype(int)  # round to int

    # Add running/queued jobs to the time series
    stats_status = df[['date', 'namespace', 'status']].value_counts()
    stats_status = stats_status.reset_index(level=0)  # move 'date' to column
    stats_status['date'] = stats_status['date'].dt.date  # remove hours
    stats_status = stats_status.groupby(['date', 'namespace', 'status']).mean()  # average hourly snapshots to daily average
    stats_status = stats_status.reset_index(level=2)  # move 'status' to column
    stats_status = stats_status.pivot(columns=['status'])[0]
    stats_status = stats_status.fillna(0)  # fill when no jobs with that status that date
    stats_status = stats_status.round(0).astype(int)  # round to int

    # Join both and save
    stats_ns = pd.concat([
        stats_ns,
        stats_status.reindex(stats_ns.index),
        ],
        axis=1)
    # After joining, timestamps with no jobs have status set to None, because those dates
    # were not present in stats_status, so we need to set them to zero
    stats_ns = stats_ns.fillna(0)
    stats_ns = stats_ns.round(0).astype(int)  # round to int
    stats_ns = stats_ns.reset_index(level=0)  # move 'date' to column

    for namespace in namespaces:
        stats_ns.loc[namespace].to_csv(
            summary_dir / f'{namespace}-timeseries.csv',
            sep=';',
            index=False,
            )

    ####################################################################################
    # Aggregate user stats per namespace (in resource-day; eg. GPU-day)                #
    ####################################################################################

    # Create a dict that groups all the snapshot that took place in a given date
    # We will use it later to perform the daily means of resources
    date_hours = sorted(set(df['date']))
    date_map = {}
    for date_hour in date_hours:
        k = date_hour.date()
        v = date_map.get(k, [])
        date_map[k] = v + [date_hour]

    # Start aggregating
    stats_user = deepcopy(df)
    stats_user = stats_user.groupby(['date', 'namespace', 'owner']).sum()  # aggregate inside hourly snapshots
    stats_user = stats_user.reset_index(level=0)  # move 'date' to column
    stats_user['date'] = stats_user['date'].dt.date  # remove hours

    # Perform the daily mean manually
    # Before we did [1]. But the problem if that it biases the measures because the
    # hours where a user have no deployments don't appear as rows in the table with cpu_num = 0.
    # The row simply does not exist. So when you take the mean you are not taking into
    # the empty hours, therefore you are constantly overestimating usage. To avoid this we do the
    # mean manually by dividing the sum by the real number of snapshots that were taken that day.
    # [1]: stats_user.groupby(['date', 'namespace', 'owner']).mean()
    stats_user = stats_user.groupby(['date', 'namespace', 'owner']).sum()
    stats_user['snapshot_num'] = stats_user.index.get_level_values('date').map(lambda x: len(date_map[x]))
    stats_user = stats_user.div(stats_user['snapshot_num'], axis=0)
    stats_user = stats_user.drop(columns=['snapshot_num'])

    stats_user = stats_user.groupby(['namespace', 'owner']).sum()  # aggregate days
    stats_user = stats_user.round(0).astype(int)  # round to int
    stats_user = stats_user.reset_index(level=1)  # move 'owner' to column

    for namespace in namespaces:

        # Per user
        # Use double bracket in loc to avoid collapsing DataFrame to a Series if we only
        # have one user
        stats_user.loc[[namespace]].to_csv(
            summary_dir / f'{namespace}-users-agg.csv',
            sep=';',
            index=False,
            )

        # For the whole namespace
        ns_agg = stats_user.loc[[namespace]].sum(
            axis='rows',
            numeric_only=True,
            ).to_frame().T
        ns_agg.to_csv(
            summary_dir / f'{namespace}-full-agg.csv',
            sep=';',
            index=False
            )


if __name__ == "__main__":

    typer.run(main)

"""
Get the accounting reports for a given period.
"""

import json
from pathlib import Path

import rich
import typer


snapshot_dir = Path(__file__).resolve().parent / 'daily-snapshots'


def main(
    ini_date: str,
    end_date: str,
    ):

    # ini_date = '2023-08-01'
    # end_date = '2023-09-10'

    namespaces = ['ai4eosc', 'imagine']
    accounting ={k: {} for k in namespaces}

    for snapshot_pth in snapshot_dir.glob('**/*.json'):

        # Skip files outside the date range
        if not (ini_date <= snapshot_pth.stem <= end_date):
            continue

        # Load the snapshot
        with open(snapshot_pth, 'r') as f:
            snapshot = json.load(f)

        for namespace in namespaces:
            for job in snapshot[namespace]:

                # Discard jobs that where not running
                if job['status'] != 'running':
                    continue

                # Add to overall accounting
                for k, v in job['resources'].items():
                    accounting[namespace][k] = accounting[namespace].get(k, 0) + v

    # Convert resource to resource/hr
    for namespace in namespaces:
        for k in accounting[namespace].copy().keys():
            accounting[namespace][f'{k}/hr'] = accounting[namespace].pop(k) * 24

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

if __name__ == "__main__":
    typer.run(main)

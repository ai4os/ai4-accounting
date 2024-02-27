"""
Merge the users-stats-agg with the user-db info into a single CSV file.
"""

from pathlib import Path

import pandas as pd


main_dir = Path(__file__).resolve().parent
summary_dir = main_dir / 'summaries'
users = pd.read_csv(
    main_dir / 'users' / 'user-db.csv',
    sep=';',
)

for namespace in ['ai4eosc', 'imagine']:
    stats = pd.read_csv(
        summary_dir / f'{namespace}-users-agg.csv',
        sep=';',
    )
    stats = stats.rename(columns={'owner': 'user id'})
    stats = stats.rename(columns={k: f'{k} / day' for k in stats.columns[1:]})

    # Merge both dataframes and save
    final = users.merge(stats, on='user id')
    final.to_csv(
        summary_dir / f'{namespace}-users-agg-merged.csv',
        sep=';',
        index=False,
        )

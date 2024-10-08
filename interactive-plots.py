"""
Interactive plot of stats usage.
"""

from copy import deepcopy
from pathlib import Path
from string import Template

import pandas as pd
import plotly.express as px


main_dir = Path.cwd()
html_dir = main_dir / 'htmls'
summary_dir = main_dir / 'summaries'

namespaces = ['ai4eosc', 'imagine', 'ai4life']
labels = {
    'cpu_num': 'CPU cores',
    'cpu_MHz': 'CPU frequency (MHz)',
    'memory_MB': 'RAM memory (MB)',
    'disk_MB': 'Disk memory (MB)',
    'gpu_num': ' Number of GPUs',
    'running': 'Jobs running',
    'queued': 'Jobs queued',
}

# Load html template
with open(html_dir / 'template.html', 'r') as f:
    html_template = Template(f.read())

# Generate plots
for namespace in namespaces:

    df = pd.read_csv(
        summary_dir / f'{namespace}-timeseries.csv',
        sep=';',
    )

    with open(html_dir / f'{namespace}.html', 'w') as f:

        html = deepcopy(html_template)
        divs = {}

        for k in labels.keys():

            fig = px.area(
                x=df['date'],
                y=df[k],
                title=labels[k],
                labels={
                    'x': 'Dates',
                    # 'y': labels[k],
                    'y': '',
                },
                width=800, height=400,
            )
            divs[k] = fig.to_html(  # retrieve html code of the plot
                full_html=False,
                include_plotlyjs='cdn',
                )

        f.write(html.safe_substitute(divs))  # replace in template

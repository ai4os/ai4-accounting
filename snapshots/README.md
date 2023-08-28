# Usage

To use this, create first create a suitable Virtual Environment.

```bash
python -m venv --system-site-packages myenv
source myenv/bin/activate
pip install -r requirements.txt
deactivate
```

To take a snapshot of the cluster:
```bash
bash take_snapshot.sh
```
(make sure to adapt the paths in the bash script)

You can generate stats for the accounting reports with the intended start and end dates:

```bash
source ./myenv/bin/activate
python usage_stats.py 2023-09-01 2023-12-31
deactivate
```

And you will get the reports for both namespaces:

```bash
AI4EOSC accounting for the period 2023-09-01:2023-12-31
┌─────────────┬──────────┐
│  cpu_num/hr │     3408 │
│  gpu_num/hr │      408 │
│ memoryMB/hr │  8280000 │
│   diskMB/hr │ 10713600 │
└─────────────┴──────────┘
IMAGINE accounting for the period 2023-09-01:2023-12-31
┌─────────────┬────────┐
│  cpu_num/hr │    336 │
│  gpu_num/hr │      0 │
│ memoryMB/hr │ 768000 │
│   diskMB/hr │ 727200 │
└─────────────┴────────┘
```

<div align="center">
  <img src="https://ai4eosc.eu/wp-content/uploads/sites/10/2022/09/horizontal-transparent.png" alt="logo" width="500"/>
</div>


# Accounting for the AI4OS project resources

Three approaches were considered to keep the accounting:

1. Taking daily/hourly snapshots of the cluster state.
2. Using [PAPI](https://github.com/AI4EOSC/ai4-papi) to save the relevant information about the job at delete time
3. Add an additional task in the Nomad job (with `poststop` lifecycle), so that information is saved at delete time

After considering the following pros/cons of each approach, we settle for approach **(1)** as the preferred solution.

- (1) is able to account for jobs that are running but not yet deleted. Otherwise, with (2, 3), one might end up accounting in one period for the resources consumed in the previous period.
- (1, 3) are able to account for jobs that have been deleted directly by admins in the cluster, not through the API.
- (1) splits logs in several files, easier to process in chunks.
- (1, 2) save results in a clean json file, while (3) possibly relies on Consul KV store to save job information as a long string (ugly!) somewhere in Consul.
- (2, 3) generate less logs, as in (1) same long-lived jobs will appear in different snapshots. This can possibly be mitigated by consolidating logs.
- (1) is independent of PAPI, so less code clutter.

Nomad permanently sends dead jobs to garbage after [`job_gc_threshold`](https://developer.hashicorp.com/nomad/docs/configuration/server#job_gc_threshold) (4h),
so snapshots must be taken with a least a 4h interval to be able to also account for jobs deleted between snapshots. Accounting is performed up to microsecond precision.

## Usage

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

You can generate a daily summary of the logs, along with aggregation statistics per
namespace/user. Then visualize some interactive plots showing the historical usage:

```bash
python summarize.py
python interactive_plot.py
```

> :warning: Due to some side issues, CPU frequency is not very reliable around Sep 2023,
> though it will keep getting more accurate with time.

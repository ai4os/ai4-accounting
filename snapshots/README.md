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

<style>
.r1 {font-style: italic}
.r2 {color: #008080; text-decoration-color: #008080}
.r3 {color: #ffafd7; text-decoration-color: #ffafd7}
</style>

<body>
<pre style="font-family:Menlo,'DejaVu Sans Mono',consolas,'Courier New',monospace"><code>
<span class="r1">AI4EOSC accounting for the period 2023-09-01:2023-12-31</span>
┌─────────────┬──────────┐
│<span class="r2">  cpu_num/hr </span>│<span class="r3">     3408 </span>│
│<span class="r2">  gpu_num/hr </span>│<span class="r3">      408 </span>│
│<span class="r2"> memoryMB/hr </span>│<span class="r3">  8280000 </span>│
│<span class="r2">   diskMB/hr </span>│<span class="r3"> 10713600 </span>│
└─────────────┴──────────┘
<span class="r1">IMAGINE accounting for the period 2023-09-01:2023-12-31</span>
┌─────────────┬────────┐
│<span class="r2">  cpu_num/hr </span>│<span class="r3">    336 </span>│
│<span class="r2">  gpu_num/hr </span>│<span class="r3">      0 </span>│
│<span class="r2"> memoryMB/hr </span>│<span class="r3"> 768000 </span>│
│<span class="r2">   diskMB/hr </span>│<span class="r3"> 727200 </span>│
└─────────────┴────────┘
</code></pre>
</body>

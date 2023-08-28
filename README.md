<div align="center">
  <img src="https://ai4eosc.eu/wp-content/uploads/sites/10/2022/09/horizontal-transparent.png" alt="logo" width="500"/>
</div>


# Accounting for the AI4OS project resources

We will implement in parallel three different approaches for keeping the accounting of
project resources. Implementation priority order will be:

* :white_check_mark: **Daily snapshots** of the cluster state ([more info](./snapshots/README.md)).
* :hourglass_flowing_sand: **PAPI** saves at delete time the relevant information about the job
* :hourglass_flowing_sand: **Nomad job task** is created with `poststop` lifecycle, so that information is saved at delete time

Current information saved about the jobs:
* namespace
* user ID
* hardware resources (CPU, GPU, RAM, Disk)
* creation and deletion date (only for approaches 2 and 3)
* job status (only for approach 1)

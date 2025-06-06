"""
Take a snapshot of the current state of the cluster.
"""

from datetime import datetime
import json
from pathlib import Path
import re
import types

import nomad
import requests

import nomad_patches


# Disable insecure requests warning
import warnings

warnings.filterwarnings("ignore")

# Production
Nomad = nomad.Nomad()

Nomad.job.deregister_job = types.MethodType(nomad_patches.deregister_job, Nomad.job)
Nomad.job.get_allocations = types.MethodType(nomad_patches.get_allocations, Nomad.job)
Nomad.job.get_evaluations = types.MethodType(nomad_patches.get_allocations, Nomad.job)

snapshot_dir = Path(__file__).resolve().parent / "snapshots"


# Persistent requests session for faster requests
session = requests.Session()


def get_deployment(
    deployment_uuid: str,
    namespace: str,
    full_info: bool = False,
):
    """
    Retrieve the info of a specific deployment.
    Format outputs to a Nomad-independent format to be used by the Dashboard

    Parameters:
    * **vo**: Virtual Organization from where you want to retrieve your deployment
    * **deployment_uuid**: uuid of deployment to gather info about

    Returns a dict with info
    """
    j = Nomad.job.get_job(
        id_=deployment_uuid,
        namespace=namespace,
    )

    # Create job info dict
    info = {
        "job_ID": j["ID"],
        "name": j["Name"],
        "status": "",  # do not use j['Status'] as misleading
        "owner": j["Meta"]["owner"],
        "title": j["Meta"]["title"],
        "description": j["Meta"]["description"],
        "docker_image": None,
        "docker_command": None,
        "submit_time": datetime.fromtimestamp(j["SubmitTime"] // 1000000000).strftime(
            "%Y-%m-%d %H:%M:%S"
        ),  # nanoseconds to timestamp
        "resources": {},
        "endpoints": {},
        "active_endpoints": None,
        "main_endpoint": None,
        "alloc_ID": None,
        "datacenter": None,
    }

    # Retrieve tasks
    tasks = j["TaskGroups"][0]["Tasks"]
    usertask = [t for t in tasks if t["Name"] == "main"][0]

    # Retrieve Docker image
    info["docker_image"] = usertask["Config"]["image"]
    command = usertask["Config"].get("command", "")
    args = usertask["Config"].get("args", [])
    args[:] = [str(a) for a in args]
    info["docker_command"] = f"{command} {' '.join(args)}".strip()

    # Add endpoints
    info["endpoints"] = {}
    services = j["TaskGroups"][0].get("Services", []) or []
    for s in services:
        label = s["PortLabel"]

        # Iterate through tags to find `Host` tag
        url = "missing-endpoint"
        for t in s["Tags"]:
            patterns = [
                r"Host\(`(.+?)`",
                r"HostSNI\(`(.+?)`",
            ]
            for pattern in patterns:
                match = re.search(pattern, t)
                if match:
                    url = match.group(1)
                    break

            if url != "missing-endpoint":
                break

        # Old deployments had network ports with names [deepaas, ide, monitor]
        # instead of [api, ide, monitor] so we have to manually replace them
        # see: https://github.com/AI4EOSC/ai4-papi/issues/22
        if label == "deepaas":
            label = "api"

        info["endpoints"][label] = f"https://{url}"

    # Add '/ui' to deepaas endpoint
    # If in the future we support other APIs, this will have to be removed.
    if "api" in info["endpoints"].keys():
        info["endpoints"]["api"] += "/ui"

    # Add quick-access (main endpoint) + customize endpoints
    service2endpoint = {
        "deepaas": "api",
        "jupyter": "ide",
        "vscode": "ide",
    }
    try:  # deep-start compatible service
        service = re.search(
            "deep-start --(.*)$",
            info["docker_command"],
        ).group(1)

        info["main_endpoint"] = service2endpoint[service]

    except Exception:  # return first endpoint
        endpoints = list(info["endpoints"].keys())
        info["main_endpoint"] = endpoints[0] if endpoints else None

    # Add user script for batch jobs
    if full_info:
        templates = usertask.get("Templates", []) or []
        info["templates"] = {}
        for t in templates:
            info["templates"][t["DestPath"]] = t["EmbeddedTmpl"].replace("\n ", "\n")

    # Only fill resources if the job is allocated
    allocs = Nomad.job.get_allocations(
        id_=j["ID"],
        namespace=namespace,
    )
    evals = Nomad.job.get_evaluations(
        id_=j["ID"],
        namespace=namespace,
    )
    if allocs:
        # Reorder allocations based on recency
        dates = [a["CreateTime"] for a in allocs]
        allocs = [
            x
            for _, x in sorted(
                zip(dates, allocs),
                key=lambda pair: pair[0],
            )
        ][::-1]  # more recent first

        # Select the proper allocation
        statuses = [a["ClientStatus"] for a in allocs]
        if "unknown" in statuses:
            # The node has lost connection. Avoid showing temporary reallocated job,
            # to avoid confusions when the original allocation is restored back again.
            idx = statuses.index("unknown")
        elif "running" in statuses:
            # If an allocation is running, return that allocation
            # It happens that after a network cut, when the network is restored,
            # the temporary allocation created in the meantime (now with status
            # 'complete') is more recent than the original allocation that we
            # recovered (with status 'running'), so using only recency does not work.
            idx = statuses.index("running")
        else:
            # Return most recent allocation
            idx = 0

        a = Nomad.allocation.get_allocation(allocs[idx]["ID"])

        # Add ID
        info["alloc_ID"] = a["ID"]

        # Add datacenter
        info["datacenter"] = Nomad.node.get_node(a["NodeID"])["Datacenter"]

        # Replace Nomad status with a more user-friendly status
        # Final list includes: starting, down, running, complete, failed, dead, ...
        # We use the status of the "main" task because it isn more relevant the the
        # status of the overall job (a['ClientStatus'])
        status = a["TaskStates"]["main"]["State"] if a.get("TaskStates") else "queued"
        status_map = {  # nomad: papi
            "pending": "starting",
            "unknown": "down",
        }
        info["status"] = status_map.get(
            status, status
        )  # if not mapped, then return original status

        # Add error messages if needed
        if info["status"] == "failed":
            info["error_msg"] = a["TaskStates"]["main"]["Events"][0]["Message"]

            # Replace with clearer message
            if (
                info["error_msg"]
                == "Docker container exited with non-zero exit code: 1"
            ):
                info["error_msg"] = (
                    "An error seems to appear when running this Docker container. "
                    "Try to run this Docker locally with the command "
                    f"`{info['docker_command']}` to find what is the error "
                    "or contact the module owner."
                )

        elif info["status"] == "down":
            info["error_msg"] = (
                "There seems to be network issues in the cluster. Please wait until "
                "the network is restored and you should be able to fully recover "
                "your deployment."
            )

        # Add resources
        res = a["AllocatedResources"]["Tasks"]["main"]
        gpu = (
            [d for d in res["Devices"] if d["Type"] == "gpu"][0]
            if res["Devices"]
            else None
        )
        cpu_cores = res["Cpu"]["ReservedCores"]
        info["resources"] = {
            "cpu_num": len(cpu_cores) if cpu_cores else 0,
            "cpu_MHz": res["Cpu"]["CpuShares"],
            "gpu_num": len(gpu["DeviceIDs"]) if gpu else 0,
            "memory_MB": res["Memory"]["MemoryMB"],
            "disk_MB": a["AllocatedResources"]["Shared"]["DiskMB"],
        }

        # Retrieve the node the jobs landed at in order to properly fill the endpoints
        n = Nomad.node.get_node(a["NodeID"])
        for k, v in info["endpoints"].items():
            info["endpoints"][k] = v.replace("${meta.domain}", n["Meta"]["domain"])

        # Add active endpoints
        if full_info:
            info["active_endpoints"] = []
            for k, v in info["endpoints"].items():
                try:
                    # We use GET and not HEAD, because HEAD is not returning the correct status_codes (even with "allow_redirects=True")
                    # Anyway, both latencies are almost the same when using "allow_redirects=True"
                    # * IDE deployed: GET (200), HEAD (405) | latency: ~90 ms
                    # * API not deployed: GET (502), HEAD (502) | latency: ~40 ms
                    # * Non existing domain: GET (404), HEAD (404) | latency: ~40 ms
                    r = session.get(v, timeout=2)
                    if r.ok:
                        info["active_endpoints"].append(k)
                except (
                    requests.exceptions.Timeout,
                    requests.exceptions.ConnectionError,
                ):
                    continue

        # Disable access to endpoints if there is a network cut
        if info["status"] == "down" and info["active_endpoints"]:
            info["active_endpoints"] = []

        # Replace dead status with either "complete" of "failed"
        if info["status"] == "dead":
            info["status"] = a["ClientStatus"]

    elif evals:
        # Something happened, job didn't deploy (eg. job needs port that's currently being used)
        # We have to return `placement failures message`.
        info["status"] = "error"
        info["error_msg"] = f"{evals[0].get('FailedTGAllocs', '')}"

    else:
        # info['error_msg'] = f"Job has not been yet evaluated. Contact with support sharing your job ID: {j['ID']}."
        info["status"] = "queued"

        # Fill info with _requested_ resources instead
        res = usertask["Resources"]
        gpu = (
            [d for d in res["Devices"] if d["Name"] == "gpu"][0]
            if res["Devices"]
            else None
        )
        info["resources"] = {
            "cpu_num": res["Cores"],
            "cpu_MHz": 0,  # not known before allocation
            "gpu_num": gpu["Count"] if gpu else 0,
            "memory_MB": res["MemoryMB"],
            "disk_MB": j["TaskGroups"][0]["EphemeralDisk"]["SizeMB"],
        }

    # ==================================================================================#
    # ADD SOME ACCOUNTING-SPECIFIC CODE                                                #
    # ==================================================================================#
    info["alloc_start"] = None
    info["alloc_end"] = None

    # Add allocation start and end
    if allocs:
        info["alloc_start"] = a["TaskStates"]["main"]["StartedAt"]
        info["alloc_end"] = a["TaskStates"]["main"]["FinishedAt"]

    # Dead jobs should have dead state, otherwise status will be misleading (for example)
    if j["Status"] == "dead":
        info["status"] = "dead"

    # ==================================================================================#

    return info


if __name__ == "__main__":
    print("Taking snapshot of the Nomad cluster")

    namespaces = ["ai4eosc", "imagine", "ai4life"]
    snapshot = {k: [] for k in namespaces}
    for namespace in namespaces:
        print(f"  Processing {namespace} ...")

        jobs = Nomad.jobs.get_jobs(namespace=namespace)  # job summaries
        for j in jobs:
            # Skip jobs that do not start with userjob
            # (useful for admins who might have deployed other jobs eg. Traefik)
            if not (
                j["Name"].startswith("module")
                or j["Name"].startswith("tool")
                or j["Name"].startswith("batch")
            ):
                continue

            try:
                # Retrieve details of the job
                snapshot[namespace].append(
                    get_deployment(deployment_uuid=j["ID"], namespace=namespace)
                )
            except Exception as e:
                print(f"   Failed to retrieve {j['ID']}")

    # Save snapshot
    with open(
        snapshot_dir / f"{datetime.utcnow().replace(microsecond=0).isoformat()}.json",
        "w",
    ) as f:
        json.dump(snapshot, f)

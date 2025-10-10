"""
Common configuration for all files.
"""

import nomad

# Disable insecure requests warning
import warnings

warnings.filterwarnings("ignore")


# Automatically retrieve all namespaces from Nomad
Nomad = nomad.Nomad()
NAMESPACES = [n["Name"] for n in Nomad.namespaces.get_namespaces()]
NAMESPACES.remove("default")
NAMESPACES.remove("tutorials")

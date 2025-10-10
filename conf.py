"""
Common configuration for all files.
"""

import nomad


# Automatically retrieve all namespaces from Nomad
Nomad = nomad.Nomad()
NAMESPACES = [n["Name"] for n in Nomad.namespaces.get_namespaces()]
NAMESPACES.remove("default")
NAMESPACES.remove("tutorials")

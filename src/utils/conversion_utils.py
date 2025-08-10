import json
import numpy as np

'''
Utility functions for data conversion and manipulation.
'''

def make_json_serializable(obj):
    if isinstance(obj, dict):
        return {make_json_serializable(k): make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_serializable(v) for v in obj]
    elif hasattr(obj, "value"):
        return obj.value
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    else:
        return obj

def make_csv_serializable(obj):
    if isinstance(obj, dict):
        return {k: make_csv_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_csv_serializable(v) for v in obj]
    elif hasattr(obj, "value"):
        return obj.value
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    else:
        return obj
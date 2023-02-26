import json
from typing import Dict, Any


def from_dict(data: Dict[str, Any]) -> str:
    return json.dumps({
        "body": data
    })

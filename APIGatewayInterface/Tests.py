import json
from typing import Dict, Any, Tuple


def arguments_from_dict(data: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    return {
        "body": json.dumps(data)
    }, ""

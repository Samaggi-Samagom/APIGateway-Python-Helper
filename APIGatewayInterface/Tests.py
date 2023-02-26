import json
from typing import Dict, Any, Tuple


def arguments_from_dict(data: Dict[str, Any]) -> Tuple[str, str]:
    return json.dumps({
        "body": data
    }), ""

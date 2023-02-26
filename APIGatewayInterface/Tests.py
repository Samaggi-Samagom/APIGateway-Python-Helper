import json
from typing import Dict, Any, Callable


class APIGatewayTestResponse:

    def __init__(self, data):
        self.data = data["body"]
        self.status_code = data["statusCode"]
        self.allow_cors = \
            data["headers"] == {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': '*',
                'Access-Control-Allow-Credentials': True
            } if "headers" in data else False


def post_to(func: Callable[[Dict[str, Any], Any], Dict[str, Any]], data: Dict[str, Any], context: Any = None) -> \
        APIGatewayTestResponse:
    return APIGatewayTestResponse(func(event_from_dict(data), context))


def event_from_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "body": json.dumps(data)
    }

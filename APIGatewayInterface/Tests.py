import json
from typing import Dict, Any, Callable


class APIGatewayTestResponse:

    def __init__(self, data: Dict[str, Any], function_name: str):
        self.function_name = function_name
        self.body = json.loads(data["body"])
        self.data = self.body["data"] if "data" in self.body else None
        self.message = self.body["message"] if "message" in self.body else None
        self.status_code = data["statusCode"]
        self.allow_cors = \
            data["headers"] == {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': '*',
                'Access-Control-Allow-Credentials': True
            } if "headers" in data else False

    def __str__(self):
        if self.status_code == 200:
            return f"\n\n ------ Result from {self.function_name} ------\n\n" \
                   f"Function Returned HTTP {self.status_code} with message \"{self.message}\".\n" \
                   f"Data: {self.__pretty(self.data)}\n\n" \
                   f"------ End of Result ------ \n\n"
        else:
            return f"\n\n ------ Result from {self.function_name} ------\n\n" \
                f"Function Returned Error with HTTP code {self.status_code} and message \"{self.message}\".\nThe " \
                   f"reason for the error is {self.data['reason'] if 'reason' in self.data else 'not provided'}.\n" \
                   f"Error Data: {self.__pretty(self.data['data'])}\n\n" \
                   f"------ End of Result ------ \n\n"

    @staticmethod
    def __pretty(d: Dict[str, Any]) -> str:
        return json.dumps(d, sort_keys=True, indent=4)


def post_to(func: Callable[[Dict[str, Any], Any], Dict[str, Any]], data: Dict[str, Any], context: Any = None) -> \
        APIGatewayTestResponse:
    return APIGatewayTestResponse(func(event_from_dict(data), context), func.__name__)


def event_from_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "body": json.dumps(data)
    }

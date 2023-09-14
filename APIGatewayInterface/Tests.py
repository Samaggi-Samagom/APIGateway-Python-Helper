import json
import time
import warnings
from typing import Dict, Any, Callable
from APIGatewayInterface.Responses import APIEncoder


class APIGatewayTestResponse:

    def __init__(self, data: Dict[str, Any], function_name: str, start_time: float):
        if data is None:
            warnings.warn("The lambda function did not return a value.")

            data = {
                "body": ""
            }
        self.__function_name = function_name
        self.__body = json.loads(data["body"])
        self.__data = self.body["data"] if "data" in self.body else None
        self.__message = self.body["message"] if "message" in self.body else None
        self.__status_code = data["statusCode"]
        self.__start_time = start_time
        self.__end_time = time.time()
        self.__allow_cors = \
            data["headers"] == {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': '*',
                'Access-Control-Allow-Credentials': True
            } if "headers" in data else False

    @property
    def time_taken(self):
        return self.__end_time - self.__start_time

    @property
    def status_code(self):
        return self.__status_code

    @property
    def message(self):
        return self.__message

    @property
    def body(self):
        return self.__body

    @property
    def data(self):
        return self.__data

    @property
    def function_name(self):
        return self.__function_name

    @property
    def allow_cors(self):
        return self.__allow_cors

    def __str__(self):
        if self.__status_code == 200:
            return f"\n\n ------ Result from {self.__function_name} ------\n\n" \
                   f"Function Returned HTTP {self.__status_code} with message \"{self.__message}\".\n" \
                   f"Data: {self.__pretty(self.__data)}\n\n" \
                   f"------ End of Result ------ \n\n"
        else:
            return f"\n\n ------ Result from {self.__function_name} ------\n\n" \
                f"Function Returned Error with HTTP code {self.__status_code} and message \"{self.__message}\".\nThe " \
                   f"reason for the error is {self.__data['reason'] if 'reason' in self.__data else 'not provided'}.\n" \
                   f"Error Data: {self.__pretty(self.__data['data'])}\n\n" \
                   f"------ End of Result ------ \n\n"

    @staticmethod
    def __pretty(d: Dict[str, Any]) -> str:
        return json.dumps(d, sort_keys=True, indent=2, cls=APIEncoder)

    def break_on_error(self):
        if self.__status_code != 200:
            raise RuntimeError("Server returned an error.")


def post_to(func: Callable[[Dict[str, Any], Any], Dict[str, Any]], data: Dict[str, Any], context: Any = None,
            quiet: bool = False) -> APIGatewayTestResponse:
    start_time = time.time()
    if not quiet:
        print(f"\n\n ------ Executing {func.__name__} ------ \n\n")
    res = APIGatewayTestResponse(func(event_from_dict(data), context), func.__name__, start_time)
    if not quiet:
        print(f"\n\n ------ End of Execution ------ \n\n")
    return res


def event_from_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "body": json.dumps(data)
    }


def pause():
    input("PAUSED: [Enter] to Continue")

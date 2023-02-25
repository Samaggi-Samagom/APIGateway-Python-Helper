from abc import ABC, abstractmethod
from typing import Dict, Any, List
import json
import decimal


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)


class Response(ABC):

    @staticmethod
    @abstractmethod
    def status_code():
        return -1

    @staticmethod
    @abstractmethod
    def message():
        return ""

    @staticmethod
    def _cors(data: Dict[str, Any]):
        data["headers"] = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': '*',
            "Access-Control-Allow-Credentials": True
        }
        return data

    def _raw_response(self, data: Dict[str, Any], allow_cors: bool):
        data = {
                "statusCode": self.status_code(),
                "body": json.dumps({
                    "message": self.message(),
                    "data": data
                }, cls=DecimalEncoder)
            }

        if allow_cors:
            print(self._cors(data))
            return self._cors(data)
        else:
            print(data)
            return data


def cors(data: Dict[str, Any]):
    data["headers"] = {
        'Access-Control-Allow-Headers': 'Content-Type,authorisation',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': '*'
    }
    return data


class Success(Response):

    def __init__(self, data: Dict[str, Any]):
        self._data = data

    @staticmethod
    def status_code():
        return 200

    @staticmethod
    def message():
        return "Success"

    def response(self, allow_cors):
        return self._raw_response(self._data, allow_cors)


class ErrorResponse(Response, ABC):

    def __init__(self, reason: str, data: dict):
        self._reason = reason
        self._data = data

    def error_response(self, allow_cors: bool = False):
        return self._raw_response(data={
            "reason": self._reason,
            "data": self._data
        }, allow_cors=allow_cors)


class BadRequest(ErrorResponse):

    @staticmethod
    def status_code():
        return 400

    @staticmethod
    def message():
        return "Bad Request"


class MissingArguments(BadRequest):

    def __init__(self, expects: List[str], got: List[str]):
        super().__init__("Missing Arguments", {"expects": list(expects), "got": list(got)})


class NotFound(ErrorResponse):

    @staticmethod
    def status_code():
        return 404

    @staticmethod
    def message():
        return "Not Found"


class Unauthorised(ErrorResponse):

    @staticmethod
    def status_code():
        return 401

    @staticmethod
    def message():
        return "Unauthorised"


class Forbidden(ErrorResponse):

    @staticmethod
    def status_code():
        return 403

    @staticmethod
    def message():
        return "Forbidden"


class InternalServerError(ErrorResponse):

    @staticmethod
    def status_code():
        return 500

    @staticmethod
    def message():
        return "Internal Server Error"


def response(resp: Response, allow_cors: bool = True) -> Dict[str, Any]:
    if issubclass(resp.__class__, ErrorResponse):
        resp: ErrorResponse
        return resp.error_response(allow_cors)
    elif isinstance(resp, Success):
        resp: Success
        return resp.response(allow_cors)
    else:
        return response(InternalServerError(
            reason=f"Cannot return response of type {resp.__class__}",
            data={}
        ))


class Arguments:

    def __init__(self, event: Dict[str, Any]):
        self._required_args = None
        self.error = None
        self._arguments = self._get_arguments(event)

    def available(self):
        return self._arguments is not None

    def should_error(self):
        return not self.available() or not self.contains_requirements()

    def _get_arguments(self, event: Dict[str, Any]):
        cleaned_body = event["body"].replace("\n", "")
        try:
            return json.loads(cleaned_body)
        except json.decoder.JSONDecodeError as e:
            self.error = BadRequest(
                reason="Unable to parse JSON request.",
                data={
                    "rawData": event["body"],
                    "error": str(e.msg)
                }
            )
            return None

    def contains(self, expected_parameters: List[str]):
        return all(x in self._arguments for x in expected_parameters)

    def contains_requirements(self):
        return all(x in self._arguments for x in self._required_args)

    @classmethod
    def __has_keys(cls, in_dict: Dict[str, Any], keys: Dict[str, dict]):
        contains = []
        for key, inner_key in keys.items():
            if inner_key is None:
                contains.append(key in in_dict.keys())
            else:
                if type(inner_key) is list:
                    contains.append(key in in_dict.keys() and all(x in in_dict[key].keys() for x in inner_key))
                else:
                    contains.append(key in in_dict.keys() and cls.__has_keys(in_dict[key], inner_key))
        return all(contains)

    def keys(self):
        return self._arguments.keys()

    def require(self, x):
        if type(x) is dict:
            self._required_args = x
        elif type(x) is list:
            self._required_args = dict((e, None) for e in x)
        else:
            raise TypeError("`require()` must be supplied with type list or dict.")

    def requirements(self):
        return self._required_args

    def __getitem__(self, item):
        return self._arguments[item]

    def get(self, item):
        return self[item]

    def raw(self):
        return self._arguments

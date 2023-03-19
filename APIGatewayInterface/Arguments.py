from __future__ import annotations

import copy

from APIGatewayInterface.Responses import MissingArguments, BadRequest, response
from typing import Dict, List, Any
import json


class ArgumentsDict(dict):

    def __init__(self, x: dict, req: Dict[str, dict | str | None], enforce_access: bool):
        super().__init__(x)
        self._raw = copy.deepcopy(x)
        self._req = req
        self._enforce_access = enforce_access

    def __getitem__(self, item):
        if self._enforce_access and item not in self._req.keys():
            raise KeyError(f"Trying to access \"{item}\" which is nested within a required member but not required.")

        if item not in self._raw:
            raise KeyError(f"Key \"{item}\" does not exist in dictionary.")

        if type(self._raw[item]) == dict:
            return ArgumentsDict(self._raw[item], self._req[item], self._enforce_access)
        else:
            return self._raw[item]


class Arguments:

    def __init__(self, event: Dict[str, Any], strict_access: bool = True):
        self._required_args = {}
        self._optional_args = []
        self.error = None
        self._arguments = self._get_arguments(event)
        self.__enforce_access = strict_access
        self.__has_requirements = False
        self.__checked_available = False
        self.__checked_requirements = False

    def available(self):
        self.__checked_available = True
        return self._arguments is not None

    def should_error(self):
        return not self.available() or not self.contains_requirements()

    def _get_arguments(self, event: Dict[str, Any]):
        cleaned_body = event["body"].replace("\n", "")
        try:
            return json.loads(cleaned_body)
        except json.decoder.JSONDecodeError as e:
            self.error = response(BadRequest(
                reason="Unable to parse JSON request.",
                data={
                    "rawData": event["body"],
                    "error": str(e.msg)
                }
            ))
            return None

    def contains(self, expected_parameters: List[str]):
        return all(x in self._arguments for x in expected_parameters)

    def contains_requirements(self):
        if not self.__checked_available and self.__enforce_access:
            raise RuntimeError("Must check if arguments are available before checking requirements.")

        contains_requirements = self.__has_keys(self._arguments, self._required_args)

        if not self.__checked_requirements and self.error is None and not contains_requirements:
            self.error = response(MissingArguments(
                expects=self.requirements(),
                got=self.keys(include_nested=True)
            ))

        self.__checked_requirements = True

        return contains_requirements

    @classmethod
    def __has_keys(cls, in_dict: Dict[str, Any], keys: Dict[str, dict]):
        contains = []
        for key, inner_key in keys.items():
            if inner_key is None:
                if type(in_dict) != dict:
                    return False
                contains.append(key in in_dict.keys())
            else:
                if type(inner_key) is list:
                    if type(in_dict[key] != dict):
                        return False
                    contains.append(key in in_dict.keys() and all(x in in_dict[key].keys() for x in inner_key))
                else:
                    if key not in in_dict:
                        return False
                    contains.append(key in in_dict.keys() and cls.__has_keys(in_dict[key], inner_key))
        return all(contains)

    @classmethod
    def __nested_keys(cls, x: Dict[str: Any]):
        res = []
        for k, v in x.items():
            if type(v) != dict:
                res.append(k)
            else:
                res.append((k, cls.__nested_keys(v)))
        return res

    def keys(self, include_nested: bool = False):
        if not include_nested:
            return self._arguments.keys()
        else:
            return self.__nested_keys(self._arguments)

    @staticmethod
    def __separate_dict(x: dict) -> List[dict]:
        res = []
        for k, v in x.items():
            res.append({k: v})
        return res

    @classmethod
    def __extract_keys(cls, x: str | dict | list):
        # print(x)
        if type(x) is str:
            return {x: None}
        elif type(x) is dict:
            as_list = []
            for d in Arguments.__separate_dict(x):
                s = list(d.items())[0]
                as_list.append((s[0], cls.__extract_keys(s[1])))
            return dict(as_list)
        elif type(x) is list:
            as_list = []
            for e in x:
                if type(e) == dict:
                    for d in Arguments.__separate_dict(e):
                        s = list(d.items())[0]
                        as_list.append((s[0], cls.__extract_keys(s[1])))
                else:
                    as_list.append((e, None))
            return dict(as_list)
        else:
            raise TypeError(f"Unable to extract requirements with type {type(x)}")

    def require(self, x):
        self.__has_requirements = True
        self._required_args = self.__extract_keys(x)

    def optional(self, x):
        if type(x) is str:
            self._optional_args = [x]
        elif type(x) is list:
            self._optional_args = x
        else:
            raise TypeError("`optional()` must be supplied with type str or list.")

    def requirements(self):
        return self._required_args

    def optionals(self):
        return self._optional_args

    def __getitem__(self, item):
        if self.__enforce_access and self.__has_requirements and \
                (not self.__checked_available or not self.__checked_requirements):
            raise RuntimeError("Accessing arguments before checking availability or requirements is potentially "
                               "unsafe. Consider checking `.available()` then `.contains_requirements()` or use "
                               "`.should_error()` before accessing first argument.")
        if self.__enforce_access and (item not in self._required_args.keys() and item not in self._optional_args):
            raise KeyError(f"Trying to access \"{item}\" which is not required nor optional.")

        if type(self._arguments[item]) == dict:
            return ArgumentsDict(self._arguments[item], self._required_args[item], self.__enforce_access)
        else:
            return self._arguments[item]

    def get(self, item):
        return self[item]

    def raw(self):
        return self._arguments

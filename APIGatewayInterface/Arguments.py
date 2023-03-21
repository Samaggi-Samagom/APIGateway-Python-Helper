from __future__ import annotations
from APIGatewayInterface.Responses import MissingArguments, BadRequest, response
from typing import Dict, List, Any, Tuple
import json
import copy


class ArgumentsDict(dict):

    def __init__(self, x: dict, req: Dict[str, dict | str | None], enforce_access: bool):
        super().__init__(x)
        self._raw = copy.deepcopy(x)
        self._req = req
        self._enforce_access = enforce_access

    def __getitem__(self, item):
        if self._req is None:
            return self._raw[item]

        if self._enforce_access and item not in self._req.keys():
            raise KeyError(f"Trying to access \"{item}\" which is not required nor optional.")

        if item not in self._raw:
            raise KeyError(f"Key \"{item}\" does not exist in dictionary.")

        if type(self._raw[item]) == dict:
            return ArgumentsDict(self._raw[item], self._req[item], self._enforce_access)
        else:
            return self._raw[item]

    def contains(self, x):
        return x in self._req.keys()

    def contains_all(self, strict: bool = False) -> bool:
        if strict and self._req is None:
            raise RuntimeError("Cannot use `.contain_all()` here because no requirements or optional values are "
                               "defined at this level.")
        elif self._req is None:
            return True
        else:
            return all(x in self._raw.keys() for x in self._req.keys())


class ArgumentsExtractor:

    def __init__(self, strict_access: bool, strict_unexpected: bool):
        self.__sa = strict_access
        self.__su = strict_unexpected

    def from_event(self, e: Dict[str, Any], strict_access: bool = None, strict_unexpected: bool = None) -> Arguments:
        if strict_access is None:
            strict_access = self.__sa
        if strict_unexpected is None:
            strict_unexpected = self.__su
        return Arguments(e, strict_access, strict_unexpected)


class Arguments:

    def __init__(self, event: Dict[str, Any], strict_access: bool = True, strict_unexpected: bool = True):
        self._required_args = {}
        self._optional_args = {}
        self.error = None
        self._arguments = self._get_arguments(event)
        self.__enforce_access = strict_access
        self.__enforce_unexpected = strict_unexpected
        self.__has_requirements = False
        self.__checked_available = False
        self.__checked_requirements = False

    def available(self):
        self.__checked_available = True
        return self._arguments is not None

    @classmethod
    def __contains_unexpected(cls, for_exp: Dict[str, str | dict | None], in_args: Dict[str, Any],
                              at: str = "REQUEST") -> Tuple[bool, str]:
        for k, v in in_args.items():
            new_dir = f"\"{at}\" -> \"{k}\""
            if k not in for_exp:
                return True, new_dir
            if type(v) == dict and for_exp[k] is not None:
                unexpected, loc = cls.__contains_unexpected(for_exp[k], in_args[k], at=new_dir)
                if unexpected:
                    return True, loc
        return False, ""

    def contains_unexpected(self):
        comb = self.__combine_args(self._required_args, self._optional_args)
        unexpected, loc = self.__contains_unexpected(for_exp=comb, in_args=self._arguments)
        if unexpected:
            if self.error is None:
                self.error = response(BadRequest(
                    reason="Unexpected Argument Received",
                    data={
                        "at": loc
                    }
                ))
            return True
        else:
            return False

    def should_error(self):
        return not self.available() or not self.contains_requirements() or \
            (self.contains_unexpected() and self.__enforce_unexpected)

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

    def contains(self, p: List[str] | str):
        if type(p) == list:
            return all(x in self._arguments for x in p)
        else:
            return p in self._arguments

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
        elif x is None:
            return None
        else:
            raise TypeError(f"Unable to extract arguments with type {type(x)}")

    def require(self, x):
        self.__has_requirements = True
        self._required_args = self.__extract_keys(x)

    def optional(self, x):
        self._optional_args = self.__extract_keys(x)

    def requirements(self):
        return self._required_args

    def optionals(self):
        return self._optional_args

    @classmethod
    def __combine_args(cls, x: Dict[str, str | Dict | None], y: Dict[str, str | Dict | None]):
        out = {}
        for key, value in x.items():
            if key in y:
                if type(value) != dict or type(y[key]) != dict:
                    raise TypeError("Unable to combine args due to conflicting types.")
                out[key] = cls.__combine_args(value, y[key])
            else:
                out[key] = value
        for key, value in y.items():
            if key not in out:
                out[key] = value
        return out

    def __getitem__(self, item):
        if self.__enforce_access and self.__has_requirements and \
                (not self.__checked_available or not self.__checked_requirements):
            raise RuntimeError("Accessing arguments before checking availability or requirements is potentially "
                               "unsafe. Consider checking `.available()` then `.contains_requirements()` or use "
                               "`.should_error()` before accessing first argument.")
        if self.__enforce_access and (item not in self._required_args.keys() and
                                      item not in self._optional_args.keys()):
            raise KeyError(f"Trying to access \"{item}\" which is not required nor optional.")

        if type(self._arguments[item]) == dict:
            if item in self._required_args and item in self._optional_args:
                comb_args = self.__combine_args(self._required_args, self._optional_args)
                return ArgumentsDict(self._arguments[item], comb_args[item], self.__enforce_access)
            elif item in self._required_args:
                return ArgumentsDict(self._arguments[item], self._required_args[item], self.__enforce_access)
            elif item in self._optional_args:
                return ArgumentsDict(self._arguments[item], self._optional_args[item], self.__enforce_access)
            else:
                return self._arguments[item]
        else:
            return self._arguments[item]

    def get(self, item):
        return self[item]

    def raw(self):
        return self._arguments

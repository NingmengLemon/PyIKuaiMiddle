import hashlib
import base64
import time
from urllib import parse
from typing import Any, Literal, Optional, TypeAlias
import json
import functools
import logging

import requests

from ..rwlock import ReadWriteLock

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
}

DateTypeLiteral: TypeAlias = Literal["month", "week", "day", "hour"]


class AuthError(Exception):
    """鉴权失败"""


class APIError(Exception):
    """调用错误"""


class RequestBase:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url
        self._session: Optional[requests.Session] = None

    @property
    def session(self):
        return self._session

    @property
    def base_url(self):
        return self._base_url

    def post(self, path: str, payload: Any):
        if self._session is None:
            self._session = requests.Session()
        return self._session.post(
            url=parse.urljoin(self._base_url, path),
            json=payload,
            headers=HEADERS,
        )


def check_result(func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs) -> Any:
        result = func(*args, **kwargs)
        code = result["Result"]
        msg = result["ErrMsg"]
        if code % 10000 != 0:
            logging.error("code %s: %s", code, msg)
            raise APIError(f"code {code}: {msg}")

        return result.get("Data")

    return wrapped


class IKuaiSession(RequestBase):
    def __init__(self, base_url: str, username: str, password: str) -> None:
        super().__init__(base_url)
        self._username = username
        self._password = password
        self._lock = ReadWriteLock()
        self.login()

    def login(self):
        with self._lock.write_lock():
            self._session = requests.Session()

            pw_md5 = hashlib.md5(self._password.encode()).hexdigest()
            payload = {
                "passwd": pw_md5,
                "pass": base64.b64encode(f"salt_11{pw_md5}".encode()).decode(),
                "remember_password": False,
                "username": self._username,
            }
            with self.post("/Action/login", payload=payload) as resp:
                if (code := resp.status_code) != 200:
                    self._session = None
                    raise AuthError(f"HTTP code {code}")
                result: dict = resp.json()

            if result["Result"] % 10000 != 0:
                self._session = None
                raise AuthError(result)

    @check_result
    def call(self, func_name: str, action: str, param: Any):
        with self._lock.read_lock():
            payload = {
                "func_name": func_name,
                "action": action,
                "param": param,
            }
            with self.post("/Action/call", payload=payload) as resp:
                resp.raise_for_status()
                if (code := resp.status_code) != 200:
                    raise RuntimeError(f"Unexpected HTTP code {code}")
                try:
                    return resp.json()
                except json.JSONDecodeError:
                    result = resp.content.decode("utf-8")
                    # from pyikuai
                    if "sending to kernel ..." in result:
                        return json.loads(
                            result.replace("sending to kernel ...", "").replace(
                                "\n", ""
                            )
                        )
                    raise


class IKuaiClient:
    def __init__(self, session: IKuaiSession) -> None:
        self._session = session
        self.call = session.call
        self.login = session.login

    @property
    def session(self):
        return self._session

    def get_iface_info(self):
        """获取接口信息"""
        types = ["iface_check", "iface_stream", "ether_info", "snapshoot"]
        return self.session.call("monitor_iface", "show", {"TYPE": ",".join(types)})

    def get_sys_info(self):
        """获取当前系统信息"""
        types = ["verinfo", "cpu", "memory", "stream", "cputemp"]
        return self.session.call("sysstat", "show", {"TYPE": ",".join(types)})

    def check_wans(self, poll_interval: float | int = 1):
        """检查公网出口状态"""
        types = ["internet"]
        payload = {"TYPE": ",".join(types)}
        self.session.call("iksyscheck", "start", payload)
        while not (result := self.session.call("iksyscheck", "show", payload))[
            "internet_res"
        ]:
            time.sleep(poll_interval)
        return result

    def get_conn_stat(self, datetype: DateTypeLiteral = "hour", average=True):
        """获取连接统计信息"""
        types = ["on_terminal", "conn_num", "rate_stat"]
        return self.session.call(
            "monitor_system",
            "show",
            {
                "TYPE": ",".join(types),
                "datetype": datetype,
                "math": "avg" if average else "max",
            },
        )

    def get_sys_stat(self, datetype: DateTypeLiteral = "hour", average=True):
        """获取系统统计信息"""
        types = ["cpu", "memory", "disk_space_used"]
        return self.session.call(
            "monitor_system",
            "show",
            {
                "TYPE": ",".join(types),
                "datetype": datetype,
                "math": "avg" if average else "max",
            },
        )

    def get_proto_stat(self, datetype: DateTypeLiteral = "day"):
        """获取协议统计信息"""
        return self.session.call(
            "monitor_app_flow",
            "show",
            {"TYPE": "app_history", "datetype": datetype, "interface": "all"},
        )

    def get_proto_distrib(self, minutes: int = 60):
        """获取指定持续时间长度内的协议分布"""
        return self.session.call(
            "monitor_system",
            "show",
            {"TYPE": "app_flow", "minutes": str(minutes)},
        )

import functools
import json
import logging
from typing import Any
import time
import warnings

from flask import Flask, Request, abort, jsonify, request

from .lemonyikuai import IKuaiSession, IKuaiClient
from .decorators import Scheduler, cache, compress

DEFAULT_CONFIG_FILE = "./imw_config.json"
# config content
# {
#     "username": ...,  // required
#     "password": ...,  // required
#     "base_url": ...,  // required
#     "cache_expire": ...,
#     "access_token": ...,
#     "relogin_interval": ...
# }


class UnsafeWarning(Warning):
    pass


def load_config(file: str = DEFAULT_CONFIG_FILE):
    with open(file, "r", encoding="utf-8") as fp:
        return json.load(fp)


def new_client(conf: dict):
    sess = IKuaiSession(
        base_url=conf["base_url"], username=conf["username"], password=conf["password"]
    )
    return IKuaiClient(sess)


app = Flask(__name__)
config: dict[str, Any] = load_config()
cache_expiry = config.get("cache_expire", 5)
access_token = config.get("access_token")
if not access_token:
    warnings.warn("access token not set", UnsafeWarning)
relogin_interval = config.get("relogin_interval", 3600)
ikclient = new_client(config)
relogin_scheduler = Scheduler(ikclient.login, interval=relogin_interval)


def jsonify_decorator(func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        return jsonify(func(*args, **kwargs))

    return wrapped


def trycatch_template(func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.exception(e)
            abort(500)

    return wrapped


def authorize(func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        check_auth_header(request)
        return func(*args, **kwargs)

    return wrapped


def check_auth_header(req: Request):
    if not access_token:
        return
    header = req.headers.get("Authorization", "")
    if len(split := header.split(maxsplit=1)) == 2:
        _, token = split
    else:
        token = split[0]
    if token != access_token:
        abort(401)


def api_template(rule: str, **options):
    def deco(func):
        return compress(
            app.route(rule, **options),
            jsonify_decorator,
            cache(expire=cache_expiry),
            trycatch_template,
            authorize,
        )(func)

    return deco


@api_template("/get_iface_info", methods=["GET"])
def get_iface_info():
    return ikclient.get_iface_info()


@api_template("/get_sys_info", methods=["GET"])
def get_sys_info():
    return ikclient.get_sys_info()


@api_template("/check_wans", methods=["GET"])
def check_wans():
    result = {}
    for result in ikclient.check_wans():
        time.sleep(1)
    return result


@api_template("/get_conn_stat", methods=["GET"])
def get_conn_stat():
    datetype = request.args.get("datetype", "hour")
    average = bool(request.args.get("average", True))
    return ikclient.get_conn_stat(datetype=datetype, average=average)


@api_template("/get_sys_stat", methods=["GET"])
def get_sys_stat():
    datetype = request.args.get("datetype", "hour")
    average = bool(request.args.get("average", True))
    return ikclient.get_sys_stat(datetype=datetype, average=average)


@api_template("/get_proto_stat", methods=["GET"])
def get_proto_stat():
    datetype = request.args.get("datetype", "day")
    return ikclient.get_proto_stat(datetype=datetype)


@api_template("/get_proto_distrib", methods=["GET"])
def get_proto_distrib():
    m = request.args.get("minutes", 60)
    return ikclient.get_proto_distrib(minutes=m)


relogin_scheduler.start()

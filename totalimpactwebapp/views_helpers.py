"""
A place to Get Stuff Out Of Views.

As this fills up, move into different places...this is just a handy bucket for
now, until we understand better what organization we need.
"""
import requests
import re


def remove_script_tags(str):
    inside = re.match("<script[^>]+>(.+)</script>", str)
    if inside:
        return inside.group(1)
    else:
        return ""


def bust_caches(resp):
    headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": 0
    }

    for k, v in headers.iteritems():
        resp.headers[k] = v

    return resp










#!/usr/bin/env python3
"""Authorize YouTube upload access via Google's OAuth device flow.

Made for headless/remote environments (like a Claude session): no local
browser needed. It prints a URL + short code; the channel owner opens the
URL on any device, enters the code, and approves. The resulting token is
saved to pipeline/token.json, which upload_youtube.py picks up automatically.

Requires an OAuth client of type "TVs and Limited Input devices" from
console.cloud.google.com (same project where YouTube Data API v3 is enabled).

Usage:
  python3 pipeline/device_auth.py CLIENT_ID CLIENT_SECRET

Scopes requested: youtube.upload + youtube (upload videos, set thumbnails,
manage playlists). Note: the device flow does not permit the captions scope,
so caption files are added manually in YouTube Studio (2 clicks).
"""

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

DEVICE_URL = "https://oauth2.googleapis.com/device/code"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPES = ("https://www.googleapis.com/auth/youtube.upload "
          "https://www.googleapis.com/auth/youtube")
TOKEN_FILE = Path(__file__).parent / "token.json"


def post(url, data):
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    client_id, client_secret = sys.argv[1], sys.argv[2]

    dev = post(DEVICE_URL, {"client_id": client_id, "scope": SCOPES})
    if "device_code" in dev:
        pass
    else:
        sys.exit(f"device authorization failed: {dev}")

    print("\n=== AUTHORIZE ON YOUR PHONE OR COMPUTER ===")
    print(f"1. Open:      {dev['verification_url']}")
    print(f"2. Enter code: {dev['user_code']}")
    print(f"(expires in {dev['expires_in'] // 60} minutes)\n", flush=True)

    interval = dev.get("interval", 5)
    deadline = time.time() + dev["expires_in"]
    while time.time() < deadline:
        time.sleep(interval)
        tok = post(TOKEN_URL, {
            "client_id": client_id,
            "client_secret": client_secret,
            "device_code": dev["device_code"],
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        })
        err = tok.get("error")
        if err == "authorization_pending":
            continue
        if err == "slow_down":
            interval += 2
            continue
        if err:
            sys.exit(f"authorization failed: {tok}")
        TOKEN_FILE.write_text(json.dumps({
            "token": tok["access_token"],
            "refresh_token": tok.get("refresh_token"),
            "token_uri": TOKEN_URL,
            "client_id": client_id,
            "client_secret": client_secret,
            "scopes": SCOPES.split(),
        }))
        print(f"authorized — token saved to {TOKEN_FILE}")
        print("upload_youtube.py will now work without a browser.")
        return
    sys.exit("code expired before authorization — run again")


if __name__ == "__main__":
    main()

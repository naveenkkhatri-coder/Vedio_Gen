#!/usr/bin/env python3
"""Fallback YouTube authorization for 'Desktop app' OAuth clients.

For headless environments when the device flow isn't available. Two steps:

  1. python3 manual_auth.py url CLIENT_ID
       -> prints a Google sign-in URL. Open it on any device, sign in and
          approve. The browser then tries to load http://localhost:53682/...
          and shows a "can't connect" error page — that's EXPECTED.
          Copy the ENTIRE URL from the browser's address bar.

  2. python3 manual_auth.py token CLIENT_ID CLIENT_SECRET "PASTED_URL"
       -> exchanges the code in that URL and saves pipeline/token.json,
          which upload_youtube.py uses automatically.

Scopes: youtube.upload + youtube (+ force-ssl so captions work too).
"""

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REDIRECT = "http://localhost:53682/"
SCOPES = ("https://www.googleapis.com/auth/youtube.upload "
          "https://www.googleapis.com/auth/youtube "
          "https://www.googleapis.com/auth/youtube.force-ssl")
TOKEN_FILE = Path(__file__).parent / "token.json"


def make_url(client_id):
    q = urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": REDIRECT,
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent",
    })
    return f"{AUTH_URL}?{q}"


def exchange(client_id, client_secret, pasted):
    if "code=" in pasted:
        code = urllib.parse.parse_qs(urllib.parse.urlparse(pasted).query)["code"][0]
    else:
        code = pasted.strip()
    body = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT,
    }).encode()
    req = urllib.request.Request(TOKEN_URL, data=body, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            tok = json.loads(r.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"token exchange failed: {e.read().decode()}")
    TOKEN_FILE.write_text(json.dumps({
        "token": tok["access_token"],
        "refresh_token": tok.get("refresh_token"),
        "token_uri": TOKEN_URL,
        "client_id": client_id,
        "client_secret": client_secret,
        "scopes": SCOPES.split(),
    }))
    print(f"authorized — token saved to {TOKEN_FILE}")


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "url":
        print(make_url(sys.argv[2]))
    elif len(sys.argv) == 5 and sys.argv[1] == "token":
        exchange(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        sys.exit(__doc__)

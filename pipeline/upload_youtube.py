#!/usr/bin/env python3
"""Upload a packaged video to YouTube with full metadata in one command.

Uploads the video, sets thumbnail + captions, adds it to a playlist
(creating the playlist if needed), marks it not-made-for-kids and
AI-disclosed, and applies title/description/tags from the package's
upload.json.

One-time setup (5 minutes):
  1. pip install google-api-python-client google-auth-oauthlib
  2. Google Cloud Console (console.cloud.google.com):
     create a project -> enable "YouTube Data API v3" ->
     OAuth consent screen (External, add yourself as test user) ->
     Credentials -> Create OAuth client ID (Desktop app) ->
     download JSON as client_secret.json next to this script.
  3. First run opens a browser to sign in to YOUR channel; the token is
     cached in token.json so later uploads don't ask again.

Usage:
  python3 pipeline/upload_youtube.py package/animal-encounters
  python3 pipeline/upload_youtube.py package/home-warning-signs --privacy public

Default privacy is "private" so you can review everything in YouTube
Studio and press Publish (or set a schedule) yourself. Use
--privacy public / unlisted, or --publish-at 2026-07-12T15:00:00Z to
schedule directly.
"""

import argparse
import json
import sys
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.force-ssl"]
HERE = Path(__file__).parent


def get_service():
    creds = None
    token = HERE / "token.json"
    if token.exists():
        creds = Credentials.from_authorized_user_file(str(token), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            secret = HERE / "client_secret.json"
            if not secret.exists():
                sys.exit("client_secret.json not found next to this script — "
                         "see the setup steps in the file header.")
            flow = InstalledAppFlow.from_client_secrets_file(str(secret), SCOPES)
            creds = flow.run_local_server(port=0)
        token.write_text(creds.to_json())
    return build("youtube", "v3", credentials=creds)


def upload(yt, cfg, pkg, privacy, publish_at):
    status = {"privacyStatus": privacy,
              "selfDeclaredMadeForKids": False,
              "containsSyntheticMedia": True}  # AI-content disclosure
    if publish_at:
        status["privacyStatus"] = "private"
        status["publishAt"] = publish_at
    body = {
        "snippet": {
            "title": cfg["title"],
            "description": cfg["description"],
            "tags": cfg["tags"],
            "categoryId": cfg.get("category_id", "27"),  # Education
            "defaultLanguage": "en",
            "defaultAudioLanguage": "en",
        },
        "status": status,
    }
    media = MediaFileUpload(cfg["video"], chunksize=8 * 1024 * 1024,
                            resumable=True, mimetype="video/mp4")
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    print(f"uploading {cfg['video']} ...")
    resp = None
    while resp is None:
        progress, resp = req.next_chunk()
        if progress:
            print(f"  {int(progress.progress() * 100)}%", flush=True)
    vid = resp["id"]
    print(f"video id: {vid}  https://youtu.be/{vid}")

    thumb = pkg / cfg.get("thumbnail", "thumbnail.jpg")
    if thumb.exists():
        yt.thumbnails().set(videoId=vid, media_body=str(thumb)).execute()
        print("thumbnail set")

    srt = pkg / cfg.get("captions", "captions_en.srt")
    if srt.exists():
        yt.captions().insert(
            part="snippet",
            body={"snippet": {"videoId": vid, "language": "en",
                              "name": "English", "isDraft": False}},
            media_body=MediaFileUpload(str(srt), mimetype="text/plain"),
        ).execute()
        print("captions uploaded")

    playlist = cfg.get("playlist")
    if playlist:
        pl_id = None
        pls = yt.playlists().list(part="snippet", mine=True,
                                  maxResults=50).execute()
        for pl in pls.get("items", []):
            if pl["snippet"]["title"] == playlist:
                pl_id = pl["id"]
                break
        if not pl_id:
            pl_id = yt.playlists().insert(
                part="snippet,status",
                body={"snippet": {"title": playlist,
                                  "description": cfg.get("playlist_description", "")},
                      "status": {"privacyStatus": "public"}},
            ).execute()["id"]
            print(f"playlist created: {playlist}")
        yt.playlistItems().insert(
            part="snippet",
            body={"snippet": {"playlistId": pl_id,
                              "resourceId": {"kind": "youtube#video",
                                             "videoId": vid}}},
        ).execute()
        print(f"added to playlist: {playlist}")

    print("\nDONE. Remaining manual steps in YouTube Studio:")
    print(" - add the end screen (subscribe button + video card on the outro)")
    print(" - add the info card noted in metadata.md")
    print(" - post + pin the pinned comment from metadata.md")
    if privacy == "private" and not publish_at:
        print(" - review and press Publish (or set a schedule)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("package", help="package dir containing upload.json")
    ap.add_argument("--privacy", default="private",
                    choices=["private", "unlisted", "public"])
    ap.add_argument("--publish-at", default=None,
                    help="RFC3339 UTC time to schedule, e.g. 2026-07-12T15:00:00Z")
    args = ap.parse_args()

    pkg = Path(args.package)
    cfg = json.loads((pkg / "upload.json").read_text())
    yt = get_service()
    upload(yt, cfg, pkg, args.privacy, args.publish_at)


if __name__ == "__main__":
    main()

"""Google OAuth desktop flow setup.

Usage:
    python scripts/setup_google_auth.py

Requires credentials.json (OAuth client secrets) in the working directory.
Download it from: https://console.cloud.google.com/apis/credentials
  → Create credentials → OAuth client ID → Desktop app → Download JSON

On success, writes token.json. Do NOT commit token.json to git.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    # Add Cloud NotebookLM scopes for Path B
    # "https://www.googleapis.com/auth/cloud-platform",
]


def main() -> None:
    print("Google OAuth Setup")
    print("=" * 40)
    print()

    credentials_path = Path("credentials.json")
    if not credentials_path.exists():
        print(f"Error: {credentials_path} not found.")
        print()
        print("Download OAuth client secrets from:")
        print("  https://console.cloud.google.com/apis/credentials")
        print("  → Create credentials → OAuth client ID → Desktop app → Download JSON")
        print(f"  → Save as {credentials_path}")
        sys.exit(1)

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
    except ImportError:
        print("Error: google-auth-oauthlib not installed.")
        print("Run: pip install -e '.[dev]'")
        sys.exit(1)

    token_path = Path("token.json")
    creds = None

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing existing token...")
            creds.refresh(Request())
        else:
            print("Opening browser for Google login...")
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_path, "w") as f:
            f.write(creds.to_json())
        print(f"Token saved to {token_path}")

    print()
    print("Google OAuth setup complete!")
    print(f"Token file: {token_path}")
    print()
    print("Scopes granted:")
    for scope in creds.scopes or SCOPES:
        print(f"  - {scope}")
    print()
    print("Next: run `rm-notebooklm sync --dry-run` to test reMarkable connection.")


if __name__ == "__main__":
    main()

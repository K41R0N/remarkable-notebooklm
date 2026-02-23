"""One-time reMarkable device registration.

Usage:
    python scripts/register_device.py

Prompts for the 8-character one-time code from:
  https://my.remarkable.com/device/desktop/connect

Prints the permanent device token to stdout and offers to write it to .env.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure src/ is on the path when running as a script
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def main() -> None:
    print("reMarkable Device Registration")
    print("=" * 40)
    print()
    print("1. Open: https://my.remarkable.com/device/desktop/connect")
    print("2. Copy the 8-character one-time code shown on screen.")
    print()

    code = input("Enter the 8-character code: ").strip()
    if len(code) != 8:
        print(f"Error: expected 8-character code, got {len(code)} characters.")
        sys.exit(1)

    print()
    print("Registering device...")

    try:
        from rm_notebooklm.remarkable.auth import register_device
        device_token = register_device(code)
    except NotImplementedError:
        print("Error: register_device() not yet implemented (Milestone 1).")
        sys.exit(1)

    print()
    print("Device token (permanent — store this securely):")
    print(device_token)
    print()

    write = input("Write RM_DEVICE_TOKEN to .env? [y/N] ").strip().lower()
    if write == "y":
        env_path = Path(".env")
        if not env_path.exists():
            # Copy from .env.example
            example = Path(".env.example")
            if example.exists():
                env_path.write_text(example.read_text())
            else:
                env_path.write_text("")

        content = env_path.read_text()
        if "RM_DEVICE_TOKEN=" in content:
            lines = content.splitlines()
            new_lines = [
                f"RM_DEVICE_TOKEN={device_token}" if line.startswith("RM_DEVICE_TOKEN=") else line
                for line in lines
            ]
            env_path.write_text("\n".join(new_lines) + "\n")
        else:
            with open(env_path, "a") as f:
                f.write(f"\nRM_DEVICE_TOKEN={device_token}\n")

        print(f"Written to {env_path}")

    print()
    print("Registration complete. Next step: python scripts/setup_google_auth.py")


if __name__ == "__main__":
    main()

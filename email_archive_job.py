"""Render Cron entrypoint for the read-only IMAP archive sync."""
from __future__ import annotations

import json
import sys

from email_archive import sync_imap


if __name__ == "__main__":
    result = sync_imap()
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0 if result.get("ok") else 1)

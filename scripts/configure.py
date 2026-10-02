#!/usr/bin/env python3
"""Create private local configuration. Never overwrite an existing .env."""
import secrets
from pathlib import Path

root = Path(__file__).resolve().parent.parent
target = root / '.env'
text = (root / '.env.example').read_text().replace('replace-with-at-least-50-random-characters-before-starting', secrets.token_urlsafe(64))
try:
    with target.open('x') as output:
        output.write(text)
    target.chmod(0o600)
    print('Created .env. Start with docker compose up --build -d.')
except FileExistsError:
    print('.env already exists; kept it unchanged.')

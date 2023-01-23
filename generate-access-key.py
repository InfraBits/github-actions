#!/usr/bin/env python3
import base64
import time
from typing import Optional

import click
import jwt
import requests


class GithubApp:
    _app_id: int
    _private_key: str

    def __init__(self, app_id: int, private_key: str) -> None:
        self._app_id = app_id
        self._private_key = private_key

    def _create_bearer_token(self) -> str:
        unix_now = int(time.time())
        return jwt.encode(
            payload={
                'iat': unix_now - 60,
                'exp': unix_now + 600,
                'iss': self._app_id
            },
            key=self._private_key,
            algorithm='RS256'
        )

    def _get_access_token(self, installation_id: int) -> str:
        r = requests.post(
            f'https://api.github.com/app/installations/{installation_id}/access_tokens',
            headers={
                'Authorization': f'Bearer {self._create_bearer_token()}',
            },
        )
        return str(r.json()['token'])

    def _get_installation_id(self, repository: str) -> Optional[int]:
        r = requests.get(
            f'https://api.github.com/repos/{repository}/installation',
            headers={
                'Authorization': f'Bearer {self._create_bearer_token()}',
            },
        )
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return int(r.json()['id'])

    def get_access_token(self, repository: str) -> Optional[str]:
        installation_id = self._get_installation_id(repository)
        if installation_id is None:
            return None
        return self._get_access_token(installation_id)


@click.command()
@click.option('--repo', type=str, required=True, help='GitHub repo name')
@click.option('--app-id', type=int, required=True, help='GitHub app id')
@click.option('--app-key', type=str, required=True, help='GitHub app private key')
def cli(repo: str, app_id: int, app_key: str) -> None:
    github_app = GithubApp(app_id, base64.b64decode(app_key).decode('utf-8'))
    print(github_app.get_access_token(repo))


if __name__ == '__main__':
    cli()

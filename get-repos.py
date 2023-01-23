#!/usr/bin/env python3
import base64
import json
import time
from typing import Set

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

    def get_repositories(self, installation_id: int) -> Set[str]:
        access_token = self._get_access_token(installation_id)

        results = []
        page = 0
        while True:
            r = requests.get(
                'https://api.github.com/installation/repositories',
                headers={
                    'Authorization': f'token {access_token}',
                    'Accept': 'application/vnd.github+json',
                },
                params={
                    'page': page,
                    'per_page': 100,
                }
            )
            r.raise_for_status()

            results.extend(r.json()['repositories'])

            if 'rel="next"' not in r.headers.get('Link', ''):
                break
            page += 1

        return {result['full_name'] for result in results}

    def get_installations(self) -> Set[int]:
        results = []
        page = 0
        while True:
            r = requests.get(
                'https://api.github.com/app/installations',
                headers={
                    'Authorization': f'Bearer {self._create_bearer_token()}',
                    'Accept': 'application/vnd.github+json',
                },
                params={
                    'page': page,
                    'per_page': 100,
                }
            )
            r.raise_for_status()
            results.extend(r.json())

            if 'rel="next"' not in r.headers.get('Link', ''):
                break
            page += 1

        return {result['id'] for result in results}


@click.command()
@click.option('--repo', type=str, required=False, default='', help='GitHub repo name')
@click.option('--app-id', type=int, required=True, help='GitHub app id')
@click.option('--app-key', type=str, required=True, help='GitHub app private key')
def cli(repo: str, app_id: int, app_key: str) -> None:
    github_app = GithubApp(app_id, base64.b64decode(app_key).decode('utf-8'))
    all_repos = [
        repo.lower()
        for installation_id in github_app.get_installations()
        for repo in github_app.get_repositories(installation_id)
    ]

    # Optionally filter down to a target repo
    if repo != '':
        if repo.lower() not in all_repos:
            raise ValueError(f'Unknown repo: {repo}')
        all_repos = [repo.lower()]

    print(json.dumps(all_repos))


if __name__ == '__main__':
    cli()

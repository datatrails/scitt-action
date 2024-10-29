import os
import logging
import requests

REQUEST_TIMEOUT = 30


def get_app_auth_header(fqdn: str = "app.datatrails.ai") -> str:
    """
    Get DataTrails bearer token from OIDC credentials in env
    """
    # Pick up credentials from env
    client_id = os.environ.get("DATATRAILS_CLIENT_ID")
    client_secret = os.environ.get("DATATRAILS_CLIENT_SECRET")

    if client_id is None or client_secret is None:
        raise ValueError(
            "Please configure your DataTrails credentials in the shell environment"
        )

    # Get token from the auth endpoint
    url = f"https://{fqdn}/archivist/iam/v1/appidp/token"
    response = requests.post(
        url,
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=REQUEST_TIMEOUT,
    )

    if response.status_code != 200:
        raise ValueError(
            "FAILED to acquire bearer token %s, %s", response.text, response.reason
        )

    # Format as a request header
    res = response.json()
    return f'{res["token_type"]} {res["access_token"]}'

""" Module for checking when a statement has been anchored in the append-only ledger """

import os
import argparse
import logging
import sys

from time import sleep as time_sleep

import requests


# all timeouts and durations are in seconds
REQUEST_TIMEOUT = 30
POLL_TIMEOUT = 60
POLL_INTERVAL = 10


def get_token_from_file(token_file_name: str) -> dict:
    """
    gets the token from a file,
    assume the contents of the file is the
    whole authorization header: `Authorization: Bearer {token}`
    """
    # print("Get token from file", flush=True)

    with open(token_file_name, mode="r", encoding="utf-8") as token_file:
        auth_header = token_file.read().strip()
        header, value = auth_header.split(": ")
        return {header: value}


def get_operation_status(operation_id: str, headers: dict) -> dict:
    """
    gets the operation status from the datatrails API for retrieving operation status
    """

    url = (
        f"https://app.datatrails.ai/archivist/v1/publicscitt/operations/{operation_id}"
    )

    while True:
        response = requests.get(url, timeout=30, headers=headers)

        if response.status_code == 200:
            break
        elif response.status_code == 400:
            continue
        else:
            response.raise_for_status()

    return response.json()


def poll_operation_status(
    operation_id: str, headers: dict, logger: logging.Logger
) -> str:
    """
    polls for the operation status to be 'succeeded'.
    """

    poll_attempts: int = int(POLL_TIMEOUT / POLL_INTERVAL)

    logger.info("starting to poll for operation status 'succeeded'")

    for _ in range(poll_attempts):
        try:
            operation_status = get_operation_status(operation_id, headers)

            # pylint: disable=fixme
            # TODO: ensure get_operation_status handles error cases from the rest request
            if (
                "status" in operation_status
                and operation_status["status"] == "succeeded"
            ):
                return operation_status["entryID"]

        except requests.HTTPError as e:
            logger.debug("failed getting operation status, error: %s", e)
 
        time_sleep(POLL_INTERVAL)

    raise TimeoutError("signed statement not registered within polling duration")


def main():
    """Polls for the signed statement to be registered"""

    # print("*****in-main*****", flush=True)

    parser = argparse.ArgumentParser(
        description="Polls for the signed statement to be registered"
    )

    # operation id
    parser.add_argument(
        "--operation-id",
        type=str,
        help="the operation-id from a registered statement",
    )

    # get default token file name
    home = os.environ.get("HOME")
    if home is None:
        default_token_file_name: str = ".datatrails/bearer-token.txt"
    else:
        default_token_file_name: str = home + "/.datatrails/bearer-token.txt"

    # token file name
    parser.add_argument(
        "--token-file-name",
        type=str,
        help="filename containing the token in the format"
        "of an auth header: `Authorization: Bearer {token}",
        default=default_token_file_name,
    )

    # log level
    parser.add_argument(
        "--log-level",
        type=str,
        help="log level. for any individual poll errors use DEBUG, defaults to WARNING",
        default="WARNING",
    )

    args = parser.parse_args()

    logger = logging.getLogger("check operation status")
    logging.basicConfig(level=logging.getLevelName(args.log_level))

    headers = get_token_from_file(args.token_file_name)

    try:
        entry_id = poll_operation_status(args.operation_id, headers, logger)
        print(entry_id)
    except TimeoutError as e:
        print(e, file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

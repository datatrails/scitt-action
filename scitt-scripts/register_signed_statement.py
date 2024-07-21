""" Module for submitting a SCITT signed statement to the
    DataTrails Transparency Service and optionally returning
    a Transparent Statement """

import argparse
import logging
import os
import sys
from time import sleep as time_sleep

from pycose.messages import Sign1Message
import requests

# CWT header label comes from version 4 of the scitt architecture document
# https://www.ietf.org/archive/id/draft-ietf-scitt-architecture-04.html#name-issuer-identity
HEADER_LABEL_CWT = 13

# Various CWT header labels come from:
# https://www.rfc-editor.org/rfc/rfc8392.html#section-3.1
HEADER_LABEL_CWT_ISSUER = 1
HEADER_LABEL_CWT_SUBJECT = 2

# CWT CNF header labels come from:
# https://datatracker.ietf.org/doc/html/rfc8747#name-confirmation-claim
HEADER_LABEL_CWT_CNF = 8
HEADER_LABEL_CNF_COSE_KEY = 1

# all timeouts and durations are in seconds
REQUEST_TIMEOUT = 30
POLL_TIMEOUT = 60
POLL_INTERVAL = 10


def get_dt_auth_header(logger: logging.Logger) -> str:
    """
    Get DataTrails bearer token from OIDC credentials in env
    """
    # Pick up credentials from env
    client_id = os.environ.get("DATATRAILS_CLIENT_ID")
    client_secret = os.environ.get("DATATRAILS_CLIENT_SECRET")

    if client_id is None or client_secret is None:
        logger.error(
            "Please configure your DataTrails credentials in the shell environment"
        )
        sys.exit(1)

    # Get token from the auth endpoint
    response = requests.post(
        "https://app.datatrails.ai/archivist/iam/v1/appidp/token",
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=REQUEST_TIMEOUT,
    )
    if response.status_code != 200:
        logger.error("FAILED to acquire bearer token")
        logger.debug(response)
        sys.exit(1)

    # Format as a request header
    res = response.json()
    return f'{res["token_type"]} {res["access_token"]}'


def submit_statement(
    statement_file_path: str, headers: dict, logger: logging.Logger
) -> str:
    """
    Given a Signed Statement CBOR file on disk, register it on the DataTrails
    Transparency Service over the SCITT interface
    """
    # Read the binary data from the file
    with open(statement_file_path, "rb") as data_file:
        data = data_file.read()

    # Make the POST request
    response = requests.post(
        "https://app.datatrails.ai/archivist/v1/publicscitt/entries",
        headers=headers,
        data=data,
        timeout=REQUEST_TIMEOUT,
    )
    if response.status_code != 200:
        logger.error("FAILED to submit statement")
        logger.debug(response)
        sys.exit(1)

    # Make sure it's actually in process and wil work
    res = response.json()
    if not "operationID" in res:
        logger.error("FAILED No OperationID locator in response")
        logger.debug(res)
        sys.exit(1)

    return res["operationID"]


def get_operation_status(operation_id: str, headers: dict) -> dict:
    """
    Gets the status of a long-running registration operation
    """
    response = requests.get(
        f"https://app.datatrails.ai/archivist/v1/publicscitt/operations/{operation_id}",
        headers=headers,
        timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()

    return response.json()


def wait_for_entry_id(operation_id: str, headers: dict, logger: logging.Logger) -> str:
    """
    Polls for the operation status to be 'succeeded'.
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


def attach_receipt(
    entry_id: str,
    signed_statement_filepath: str,
    transparent_statement_file_path: str,
    headers: dict,
    logger: logging.Logger,
):
    """
    Given a Signed Statement and a corresponding Entry ID, fetch a Receipt from
    the Transparency Service and write out a complete Transparent Statement
    """
    # Get the receipt
    response = requests.get(
        f"https://app.datatrails.ai/archivist/v1/publicscitt/entries/{entry_id}/receipt",
        headers=headers,
        timeout=REQUEST_TIMEOUT,
    )
    if response.status_code != 200:
        logger.error("FAILED to get receipt")
        logger.debug(response)
        sys.exit(1)

    logger.debug(response.content)

    # Open up the signed statement
    with open(signed_statement_filepath, "rb") as data_file:
        data = data_file.read()
        message = Sign1Message.decode(data)
        logger.debug(message)

    # Add receipt to the unprotected header and re-encode
    message.uhdr["receipts"] = [response.content]
    ts = message.encode(sign=False)

    # Write out the updated Transparent Statement
    with open(transparent_statement_file_path, "wb") as file:
        file.write(ts)
        logger.info("File saved successfully")


def main():
    """Creates a Transparent Statement"""

    parser = argparse.ArgumentParser(description="Create a signed statement.")

    # Signed Statement file
    parser.add_argument(
        "--signed-statement-file",
        type=str,
        help="filepath to the Signed Statement to be registered.",
        default="signed-statement.cbor",
    )

    # Output file
    parser.add_argument(
        "--output-file",
        type=str,
        help="output file to store the Transparent Statement (leave blank to skip saving).",
        default="",
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

    # Get auth
    auth_headers = {"Authorization": get_dt_auth_header(logger)}

    # Submit Signed Statement to DataTrails
    op_id = submit_statement(args.signed_statement_file, auth_headers, logger)
    logging.info("Successfully submitted with Operation ID %s", op_id)

    # If the client wants the Transparent Statement, wait for it
    if args.output_file != "":
        logging.info("Now waiting for registration to complete")

        # Wait for the registration to complete
        try:
            entry_id = wait_for_entry_id(op_id, auth_headers, logger)
        except TimeoutError as e:
            logger.error(e)
            sys.exit(1)

        logger.info("Fully Registered with Entry ID %s", entry_id)

        # Attach the receipt
        attach_receipt(
            entry_id, args.signed_statement_file, args.output_file, auth_headers, logger
        )


if __name__ == "__main__":
    main()

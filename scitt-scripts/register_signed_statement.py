""" Module for submitting a SCITT signed statement to the
    DataTrails Transparency Service and optionally returning
    a Transparent Statement """

import argparse
import logging
import os
import sys
from time import sleep as time_sleep
import requests

from pycose.messages import Sign1Message

from api_requests import get_app_auth_header
from v3leafhash import leaf_hash
from verify_receipt import verify_receipt

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
POLL_TIMEOUT = 120
POLL_INTERVAL = 10

DATATRAILS_URL_DEFAULT="https://app.datatrails.ai"


def submit_statement(
    statement_file_path: str,
    headers: dict,
    logger: logging.Logger,
    datatrails_url: str = DATATRAILS_URL_DEFAULT,
) -> str:
    logging.info("submit_statement()")
    """
    Given a Signed Statement CBOR file on disk, register it on the DataTrails
    Transparency Service over the SCITT interface
    """
    # Read the binary data from the file
    with open(statement_file_path, "rb") as data_file:
        data = data_file.read()

    logging.info("statement_file_path opened: %s", statement_file_path)
    # Make the POST request
    response = requests.post(
        f"{datatrails_url}/archivist/v1/publicscitt/entries",
        headers=headers,
        data=data,
        timeout=REQUEST_TIMEOUT,
    )
    if response.status_code != 200:
        logger.debug("FAILED to submit statement response.raw: %s", response.raw)
        logger.debug("FAILED to submit statement response.text: %s", response.text)
        logger.debug("FAILED to submit statement response.reason: %s", response.reason)
        logger.debug(response)
        raise Exception("Failed to submit statement")

    # Make sure it's actually in process and wil work
    res = response.json()
    if not "operationID" in res:
        raise Exception("FAILED No OperationID locator in response")

    return res["operationID"]


def get_operation_status(
    operation_id: str, headers: dict, datatrails_url: str = DATATRAILS_URL_DEFAULT
) -> dict:
    """
    Gets the status of a long-running registration operation
    """
    response = requests.get(
        f"{datatrails_url}/archivist/v1/publicscitt/operations/{operation_id}",
        headers=headers,
        timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()

    return response.json()


def wait_for_entry_id(
    operation_id: str,
    headers: dict,
    logger: logging.Logger,
    datatrails_url: str = DATATRAILS_URL_DEFAULT,
) -> str:
    """
    Polls for the operation status to be 'succeeded'.
    """

    poll_attempts: int = int(POLL_TIMEOUT / POLL_INTERVAL)

    logger.info("starting to poll for operation status 'succeeded'")

    for _ in range(poll_attempts):
        try:
            operation_status = get_operation_status(operation_id, headers, datatrails_url)

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


def get_receipt(entry_id: str, request_headers: dict, datatrails_url: str = DATATRAILS_URL_DEFAULT):
    """Get the receipt for the provided entry id"""
    # Get the receipt
    response = requests.get(
        f"{datatrails_url}/archivist/v1/publicscitt/entries/{entry_id}/receipt",
        headers=request_headers,
        timeout=REQUEST_TIMEOUT,
    )
    if response.status_code != 200:
        raise Exception("FAILED to get receipt")

    return response.content


def attach_receipt(
    receipt: bytes,
    signed_statement_filepath: str,
    transparent_statement_file_path: str,
):
    """
    Given a Signed Statement file on disc and the provided receipt content, from the Transparency Service,
    read the statement fromm disc, attach the provided receipt, writing the re-encoded result back to disc.
    The resulting re-encoded statement is now a Transparent Statement.

    The caller is expected to have *verified* the receipt first.
    """

    # Open up the signed statement
    with open(signed_statement_filepath, "rb") as data_file:
        data = data_file.read()
        message = Sign1Message.decode(data)

    # Add receipt to the unprotected header and re-encode
    message.uhdr["receipts"] = [receipt]
    ts = message.encode(sign=False)

    # Write out the updated Transparent Statement
    with open(transparent_statement_file_path, "wb") as file:
        file.write(ts)


def get_leaf_hash(entry_id: str, datatrails_url: str = DATATRAILS_URL_DEFAULT) -> str:
    """Obtain the leaf hash for a given Entry ID

    The leaf hash is the value that is proven by the COSE Receipt attached to the transparent statement.

    For SCITT Statements registered with datatrails, the leaf hash currently includes content
    that is additional to the signed statement.
    It currently requires a proprietary API call to DataTrails to obtain that content.
    The content is available on a public access endpoint (no authorisation is required)

    These limitations are not inherent to the SCITT architecture.
    The are specific to the current DataTrails implementation, and will be addressed in future releases.

    Note that the leaf hash can be read directly from the merkle log given only information in the receipt.
    And, as the log data is public and easily replicable, this does not require interaction with datatrails.

    However, on its own, this does not show that the leaf hash commits the statement to the log.
    """
    identity = api_entryid_to_identity(entry_id)
    public_url = f"{datatrails_url}/archivist/v2/public{identity}"
    response = requests.get(public_url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    event = response.json()
    return leaf_hash(event)


def api_entryid_to_identity(entryid: str) -> str:
    """
    Convert a SCITT Entry ID to a DataTrails Event Identity
    """
    eventsplit = entryid.split("_events_")
    eventUUID = eventsplit[-1]

    bucketsplit = eventsplit[0].split("assets_")
    bucketUUID = bucketsplit[-1]

    return f"assets/{bucketUUID}/events/{eventUUID}"


def get_dt_auth_header(logger: logging.Logger, fqdn: str) -> str:
    """
    Get DataTrails bearer token from OIDC credentials in env
    """
    try:
        return get_app_auth_header(fqdn=fqdn)
    except Exception as e:
        logger.error(repr(e))
        sys.exit(1)


def main():
    """Creates a Transparent Statement"""

    parser = argparse.ArgumentParser(description="Create a signed statement.")
    parser.add_argument(
        "--datatrails-url",
        type=str,
        help="The url of the DataTrails transparency service.",
        default=DATATRAILS_URL_DEFAULT,
    )

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
    parser.add_argument(
        "--verify",
        help="verify the result of registraion",
        default=False,
        action="store_true",
    )

    args = parser.parse_args()

    logger = logging.getLogger("check operation status")
    logging.basicConfig(level=logging.getLevelName(args.log_level))

    # Get auth
    logging.info("Get Auth Headers")
    try:
        auth_headers = {"Authorization": get_app_auth_header(args.datatrails_url)}
    except Exception as e:
        logger.error(repr(e))
        sys.exit(1)

    # Submit Signed Statement to DataTrails
    logging.info("submit_statement: %s", args.signed_statement_file)

    op_id = submit_statement(
        args.signed_statement_file, auth_headers, logger, datatrails_url=args.datatrails_url
    )
    logging.info("Successfully submitted with Operation ID %s", op_id)

    # If the client wants the Transparent Statement or receipt, wait for registration to complete
    if args.verify or args.output_file != "":
        logging.info("Waiting for registration to complete")
        # Wait for the registration to complete
        try:
            entry_id = wait_for_entry_id(op_id, auth_headers, logger, datatrails_url=args.datatrails_url)
        except TimeoutError as e:
            logger.error(e)
            sys.exit(1)
            logger.info("Fully Registered with Entry ID %s", entry_id)

        leaf = get_leaf_hash(entry_id, datatrails_url=args.datatrails_url)
        logger.info("Leaf Hash: %s", leaf.hex())

    if args.verify or args.output_file != "":
        # Don't attach the receipt without verifying the log returned a receipt
        # that genuinely represents the expected content.

        receipt = get_receipt(entry_id, auth_headers, datatrails_url=args.datatrails_url)
        if not verify_receipt(receipt, leaf):
            logger.info("Receipt verification failed")
            sys.exit(1)

    if args.output_file == "":
        return

    # Attach the receipt
    attach_receipt(
        receipt, args.signed_statement_file, args.output_file
    )
    logger.info(f"File saved successfully {args.output_file}")


if __name__ == "__main__":
    main()

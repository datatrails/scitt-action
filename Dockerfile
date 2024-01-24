# Container image that runs your code
FROM python:3.12-alpine

# Upgrade bash, and curl
RUN apk add --no-cache --upgrade bash
RUN apk add curl

# Install jq
RUN apk add --no-cache jq # httpie

COPY ./scitt-scripts/ /scripts/
WORKDIR /scripts
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

ENTRYPOINT ["/scripts/entrypoint.sh"]

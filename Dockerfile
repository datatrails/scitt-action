# Container image that runs your code
FROM python:3.12-alpine

RUN apk add --no-cache --upgrade bash
RUN apk add curl

# Install jq
RUN apk add --no-cache jq # httpie
RUN echo '{"foo": "bar"}' | jq

# Copies your code file from your action repository to the filesystem path `/` of the container
COPY ./scitt-scripts/ .

ENTRYPOINT ["/entrypoint.sh"]

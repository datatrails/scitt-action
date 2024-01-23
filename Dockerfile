# Container image that runs your code
FROM python:3.12

# Copies your code file from your action repository to the filesystem path `/` of the container
COPY ./scitt-scripts/ /.

# Code file to execute when the docker container starts up (`entrypoint.sh`)
ENTRYPOINT ["/create-token.sh"]

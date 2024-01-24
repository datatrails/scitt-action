# scitt-action
GitHub Action for DataTrails implementation of SCITT

## Sample Code

This action prints "Hello World" or "Hello" + the name of a person to greet to the log.

## Inputs

## `who-to-greet`

**Required** The name of the person to greet. Default `"World"`.

## Outputs

## `time`

The time we greeted you.

## Example usage

## Build Locally

docker build -t datatrails/scitt-action:v0.3.1 .

## Run Locally

docker run datatrails/scitt-action:v0.3.1 a b c d
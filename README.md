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

uses: actions/hello-world-docker-action@v2
with:
  who-to-greet: 'Mona the Octocat'

git add action.yml entrypoint.sh Dockerfile README.md
git commit -m "GitHub Action sample"
git tag -a -m "First action release-test" v0.1
git push --follow-tags

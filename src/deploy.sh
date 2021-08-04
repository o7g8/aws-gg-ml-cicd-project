#!/bin/bash -e

if [[ $# -ne 1 ]] || ([[ $1 != "test" ]] && [[ $1 != "prod" ]]); then
  echo "Usage $0 <deployment environment (test|prod)>"
  exit 1
fi

DEPLOYMENT_ENVIRONMENT=$1
STACK_NAME="gg-cicd-application-${DEPLOYMENT_ENVIRONMENT}-stack"

sam package \
    --template-file template.yml \
    --output-template-file packaged.yml \
    --s3-bucket ${ARTIFACTS_BUCKET}

sam deploy \
    --template-file packaged.yml \
    --stack-name ${STACK_NAME} \
    --capabilities CAPABILITY_IAM \
    --parameter-overrides CoreName=gg-cicd-${DEPLOYMENT_ENVIRONMENT} \
    --no-fail-on-empty-changeset

GROUP_ID=`aws cloudformation describe-stacks --stack-name ${STACK_NAME} --query 'Stacks[0].Outputs[0].OutputValue' --output text`
GROUP_VERSION_ID=`aws greengrass list-group-versions --group-id ${GROUP_ID} --query 'Versions[0].Version' --output text`

aws greengrass create-deployment --group-id ${GROUP_ID} --group-version-id "${GROUP_VERSION_ID}" --deployment-type NewDeployment

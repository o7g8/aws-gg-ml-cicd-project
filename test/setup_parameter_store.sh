#!/bin/bash -e

THING_NAME="integration-testing-client"
POLICY_NAME="gg-cicd-test-integration-test-client"

#######################################################################
# Make Certificates and stored them in Systems Manager Parameter Store
#######################################################################
cd certs

CERTIFICATE_ARN=`
  aws iot create-keys-and-certificate \
    --set-as-active \
    --certificate-pem-outfile "${THING_NAME}.cert.pem" \
    --public-key-outfile "${THING_NAME}.public.key" \
    --private-key-outfile "${THING_NAME}.private.key" \
    --output text \
    --query 'certificateArn'`
CERTIFICATE_ID=`echo $CERTIFICATE_ARN | sed 's/.*\///'`

aws ssm put-parameter --name /gg-cicd-test/integration-testing-client.cert.pem --type SecureString --overwrite --value "`cat ${THING_NAME}.cert.pem`"
aws ssm put-parameter --name /gg-cicd-test/integration-testing-client.private.key --type SecureString --overwrite --value "`cat ${THING_NAME}.private.key`"

cd ..

#######################################################################
# Attach a policy to the certificates that lets us publish/subscribe
#######################################################################
aws iot create-policy \
    --policy-name  ${POLICY_NAME} \
    --policy-document '{"Version": "2012-10-17", "Statement": [{"Effect": "Allow","Action": ["iot:Connect","iot:Publish","iot:Subscribe","iot:Receive","iot:GetThingShadow","iot:UpdateThingShadow","iot:DeleteThingShadow"],"Resource": "*"}]}'

sleep 5 # need a little delay for attach-policy to see the policy

aws iot attach-policy \
    --policy-name  ${POLICY_NAME} \
    --target ${CERTIFICATE_ARN}

#######################################################################
# Store our IoT Core Endpoint in a Systems Manager Parameter
#######################################################################
IOT_ENDPOINT=`aws iot describe-endpoint --endpoint-type iot:Data-ATS --query 'endpointAddress' --output text`
aws ssm put-parameter --name /gg-cicd-test/IOT_ENDPOINT --type SecureString --overwrite --value ${IOT_ENDPOINT}


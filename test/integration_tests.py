from datetime import datetime
import json
import logging
import os
import time
import unittest
import uuid
import warnings

from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import boto3


# Setup Logging
logger = logging.getLogger("AWSIoTPythonSDK.core")
logger.setLevel(logging.ERROR)
streamHandler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
streamHandler.setFormatter(formatter)
logger.addHandler(streamHandler)


# Constants
SUBSCRIPTION_PORT = 8883
MESSAGE_WAIT_TIME = 5  # seconds

IOT_ENDPOINT = os.environ['IOT_ENDPOINT']  # This is specific to your AWS Account and Region

# Helper Functions

# Suppress warning from AWSIoTMQTTClient when run in unittest
# We do this to quiesce a harmless warning introduced in a recent version of the client library.
def ignore_warnings(test_func):
    def do_test(self, *args, **kwargs):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ResourceWarning)
            test_func(self, *args, **kwargs)
    return do_test


def echo_response_is_valid(message, response):

    # A valid response contains the same KV pairs as the message
    for key in message.keys():
        if message[key] != response[key]:
            logger.error(f'message: {message} response: {response}')
            return False

    return True


def listen_on_topic(client_id, response_topic):
    # point to our client certificates
    cert_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'certs/')
    ca_file_path = cert_path + 'root.ca.pem'
    private_key_file_path = cert_path + 'integration-testing-client.private.key'
    certificate_file_path = cert_path + 'integration-testing-client.cert.pem'

    # Configure MQTT Client
    mqtt_client = AWSIoTMQTTClient(client_id)
    mqtt_client.configureEndpoint(IOT_ENDPOINT, SUBSCRIPTION_PORT)
    mqtt_client.configureCredentials(ca_file_path, private_key_file_path, certificate_file_path)
    mqtt_client.configureConnectDisconnectTimeout(10)  # 10 sec
    mqtt_client.configureMQTTOperationTimeout(5)  # 5 sec

    # Connect to message broker
    mqtt_client.connect()

    # subscribe to the topic and register message handler
    mqtt_client.subscribe(response_topic, 1, subscribe_callback)


def subscribe_callback(client, userdata, message):
    logger.info('Message received with payload %s' % message.payload + 'and topic %s' % message.topic)

    payload = json.loads(message.payload)
    message_id = payload['id']
    payload['topic'] = message.topic

    # save the received message for our test to validate
    rm = get_received_messages()
    key = ':'.join([message_id, message.topic])
    rm[key] = payload
    set_received_messages(rm)

    return True


def get_received_messages():
    global received_messages
    return received_messages


def set_received_messages(rm):
    global received_messages
    received_messages = rm


# State
received_messages = {}


class TestSampleFunction(unittest.TestCase):

    def setUp(self):
        set_received_messages({})

    @ignore_warnings
    def test_echo(self):
        input_topic = 'gg-cicd-test/in'
        output_topic = 'gg-cicd-test/out'

        listen_on_topic(client_id='TestSampleFunction.test_echo', response_topic=output_topic)

        iot_client = boto3.client('iot-data')

        message = {
            'id': str(uuid.uuid4()),
            'processed_at': str(datetime.now())
        }

        received_valid_response = False
        for i in range(5):
            if received_valid_response:
                break

            iot_client.publish(topic=input_topic, qos=1, payload=json.dumps(message))
            time.sleep(MESSAGE_WAIT_TIME)

            responses = get_received_messages()

            key = ':'.join([message['id'], output_topic])
            if key in responses:
                received_valid_response = echo_response_is_valid(message, responses[key])

        assert received_valid_response



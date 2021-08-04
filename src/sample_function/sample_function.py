import os
import json
from datetime import datetime
import greengrasssdk


counter = 0
client = greengrasssdk.client('iot-data')

def function_handler(event, context):
    '''Echo message on /in topic to /out topic'''

    response = json.loads(event)

    # maybe do something with the event before sending it back

    response_string = json.dumps(response)

    client.publish(
        topic='{}/out'.format(os.environ['CORE_NAME']),
        payload=response_string
    )

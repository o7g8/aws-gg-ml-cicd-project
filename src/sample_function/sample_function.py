import os
import json
from datetime import datetime
import greengrasssdk


counter = 0
client = greengrasssdk.client('iot-data')

def function_handler(event, context):
    '''Echo message on /in topic to /out topic'''

    response = json.loads(event)

    # Add the time we processed the message to our response (with failure)
    # response['processed_at'] = str(datetime.now())
    # the working version
    response['echo_processed_at'] = str(datetime.now())
    print('!!!!!!!! hello !!!!')

    response_string = json.dumps(response)

    client.publish(
        topic='{}/out'.format(os.environ['CORE_NAME']),
        payload=response_string
    )

#
# lambda_function.py
#

# function for Greengrass ML Inference
# Loads model based on cifar10 dataset 
#

import greengrasssdk
import json
import logging
import numpy as np
import magic
import mxnet as mx
import os
import sys
import time

from datetime import datetime
from mxnet import autograd as ag
from mxnet import gluon
from mxnet.gluon.model_zoo import vision as models
from skimage import io
from skimage.transform import resize
from time import strftime
from threading import Timer

#
# global vars
#
model_dir = '/models/image-classification'
image_dir = '/images'

topic = 'greengrass/ml/inference/{}/'.format(os.environ['AWS_IOT_THING_NAME'])

class_names = ['airplane', 'automobile', 'bird', 'cat', 'deer',
               'dog', 'frog', 'horse', 'ship', 'truck']

#
# configure logging
#
logger = logging.getLogger()

for h in logger.handlers:
    logger.removeHandler(h)
h = logging.StreamHandler(sys.stdout)

FORMAT = "[%(asctime)s - %(levelname)s - %(filename)s:%(lineno)s - %(funcName)s - %(message)s"
h.setFormatter(logging.Formatter(FORMAT))

logger.addHandler(h)
logger.setLevel(logging.INFO)

class RequestIdAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        return '%s]: %s' % (self.extra['request_id'], msg), kwargs

#
# functions
#
def np_array_to_str(data):
    return str(data.tolist())


# function borrowed from sagemaker cifar10 example
# added resizing
def read_image(filename):
    img = io.imread(filename)
    shape = img.shape
    logger.info("filename: {} shape: {}".format(filename, shape))

    if shape[0] > 32 or shape[1] > 32:
        logger.info("resizing image to 32x32")
        img = resize(img, (32, 32), mode='constant', anti_aliasing=False)

    img = np.array(img).transpose(2, 0, 1)
    img = np.expand_dims(img, axis=0)
    return img


# function borrowed from sagemaker cifar10 example but added some logging statements
def transform_fn(net, data, input_content_type, output_content_type):
    logger.debug("net: {}".format(net))
    logger.debug("data: {}".format(data))
    logger.debug("type data: {}".format(type(data)))
    logger.debug("input_content_type: {}".format(input_content_type))
    logger.debug("output_content_type: {}".format(output_content_type))
    """
    Transform a request using the Gluon model. Called once per request.

    :param net: The Gluon model.
    :param data: The request payload.
    :param input_content_type: The request content type.
    :param output_content_type: The (desired) response content type.
    :return: response payload and content type.
    """
    # we can use content types to vary input/output handling, but
    # here we just assume json for both
    parsed = json.loads(data)
    logger.debug("parsed: {}".format(parsed))
    nda = mx.nd.array(parsed)
    output = net(nda)
    prediction = mx.nd.argmax(output, axis=1)
    logger.info("prediction: {}".format(prediction))
    response_body = json.dumps(prediction.asnumpy().tolist()[0])
    logger.info("response_body: {} output_content_type: {}".format(response_body, output_content_type))
    return response_body, output_content_type


def classify_image(image_name):
    img = read_image(image_name)

    logger.info("type img: {}".format(type(img)))

    s_img = np_array_to_str(img)
    logger.info("type s_img: {}".format(type(s_img)))

    response_body, output_content_type = transform_fn(net, s_img, 'application/json', 'application/json')
    image_class = class_names[int(float(response_body))]
    logger.info("image_name: {} image_class: {}".format(image_name, image_class))
    return image_class


def move_processed_image(file):
    processed_dir = image_dir + '/.processed'
    if not os.path.exists(processed_dir):
        try:
            os.makedirs(processed_dir)
        except Exception as e:
            logger.error("failed to created directory {}: {}".format(processed_dir, e))
            return
    new_file = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f") + '_' + file
    src = image_dir + '/' + file
    dst = processed_dir + '/' + new_file
    logger.info("moving file from {} to {}".format(src, dst))
    os.rename(src, dst)


def gg_runner():
    try:
        dirs = os.listdir(image_dir)
        logger.info("dirs: {}".format(dirs))

        for file in dirs:
            abs_file_path = image_dir + '/' + file
            #stat = os.stat(abs_file_path)
            detected = magic.detect_from_filename(abs_file_path)
            logger.info("file: {} mime-type: {} encoding: {} file type name: {}".format(file, detected.mime_type, detected.encoding, detected.name))
            if detected.mime_type == 'image/png' or detected.mime_type == 'image/jpeg':
                client.publish(topic=topic, payload=json.dumps({"info": "found image"}))
                logger.info("found image, trying to classify")
                image_class = classify_image(abs_file_path)
                client.publish(topic=topic, payload=json.dumps({"image": file, "class": image_class}))
                move_processed_image(file)

    except Exception as e:
        logger.error("failed to process images in image_dir {}: {}".format(image_dir, e))

    Timer(5, gg_runner).start()


logger.info("create greengrass client")
client = greengrasssdk.client('iot-data')

client.publish(topic=topic, payload=json.dumps({"info": "loading model"}))
logger.info("loading model")
net = models.get_model('resnet34_v2', ctx=mx.cpu(), pretrained=False, classes=10)
net.load_parameters('%s/model.params' % model_dir, ctx=mx.cpu())
logger.info("net: {}".format(net))


gg_runner()

def lambda_handler(event, context):
    logger.info("event: " + str(event))

    return True

"""
This is a very inefficient way of doing inference, but it will do for now
models are not optimized and we are simply using keras and other dev tools to do inference
only if we have some real production volume
then we will we need tensorflow serving, probably in a docker container
"""
import numpy as np
import requests
from PIL import Image
from io import BytesIO

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.images import ImageFile


def call_encoder(pixels:np.ndarray):
    """returns vector embedding of a single image as np array"""
    url = "http://" + "/".join([
        settings.INFERENCE_HOST,
        "v1/models",
        settings.ENCODER_NAME
    ]) + ":predict"
    data = {
        "instances": [pixels]
    }
    response = requests.post(url,json=data)
    return response.json()['predictions'][0]


# TODO : rebuild model to have a single concatenated input
# see : https://www.tensorflow.org/tfx/serving/signature_defs
def call_differenciator(batch_left, batch_right):
    """returns sameness for the entire batch"""
    # combine two halfs into a single batch
    batch = np.concatenate([batch_left,batch_right], axis=1)

    # call tf serving API
    url = "http://" + "/".join([
        settings.INFERENCE_HOST,
        "v1/models",
        settings.ENCODER_NAME
    ]) + ":predict"
    data = {
        "instances" : [batch]
    }
    response = requests.post(url,json=data)
    return response.json()['predictions']


def get_square_box(width, height):
    """returns a 4 tuple pil coord box 1:1 for a given image obj"""

    def _long_to_short(lower, higher, target_width):
        """returns tuple new lower, new higher seperated by target_width"""
        crop_one_side = (higher - lower - target_width) // 2
        return lower + crop_one_side, higher - crop_one_side

    # make a bounding box of the whole image
    box = [0, 0, width, height]
    # center crop long side to fit 1:1
    if box[2] > box[3]:
        box[0], box[2] = _long_to_short(0,box[2],box[3])
    elif box[2] < box[3]:
        box[1], box[3] = _long_to_short(0,box[3],box[2])
    return box


def standardize_image(input_image: ImageFile, new_size=settings.IMAGE_SIZE) -> (ImageFile, np.ndarray):
    """
    returns a new ImageFile of specified size, free of metadata
    and pixels stored in np array
    """

    # first open the image in PIL
    old_image = Image.open(input_image)

    # resize to 1:1 then get pixels
    pixels = np.array(
        old_image.resize(new_size,box=get_square_box(*old_image.size))
    )

    # make a new pil image file then django file
    new_image = Image.fromarray(pixels,mode="RGB")
    temp_file = BytesIO()
    new_image.save(fp=temp_file,format="PNG")
    return ImageFile(temp_file), pixels.reshape((-1,*new_size,3))


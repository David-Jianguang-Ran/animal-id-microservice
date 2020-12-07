from django.core.files.base import ContentFile

from PIL import Image
from io import BytesIO

import numpy as np
import random


def get_fake_image_file():
    # make a 9 * 9 * 3 test image
    # it should look a three stripes of RGB, like a flag, but really noisy
    image_data = np.array(
        [[random.randint(0,255) if j % 3 == i else 0 for j in range(9*9)] for i in range(3)]
    ).astype("int8").reshape((9,9,3))
    image_obj = Image.fromarray(image_data,mode="RGB")
    to_file = BytesIO()
    image_obj.save(fp=to_file,format="PNG")
    return ContentFile(to_file.getvalue())


def get_test_embeddings():
    # returns some 4 vectors from the encoder
    return [
        [104.171407, 114.440775, -120.054556, -106.2461677],  # <= clearly this one is not like the others
        [4.638023,  7.8766  , -23.59152 , -7.3079066],
        [7.703525,  4.752338, -21.905794, -9.553763 ],
        [4.171407, 14.440775, -20.054556, -6.2461677],
    ]
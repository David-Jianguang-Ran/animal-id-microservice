"""
This is a very inefficient way of doing inference, but it will do for now
models are not optimized and we are simply using keras and other dev tools to do inference
only if we have some real production volume
then we will we need tensorflow serving, probably in a docker container
"""
import numpy as np
from PIL import Image
from io import BytesIO

from tensorflow.keras.models import load_model, Model
from tensorflow.keras.applications.inception_v3 import preprocess_input
from tensorflow_addons.losses import TripletHardLoss,TripletSemiHardLoss

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.images import ImageFile


class YouOnlyLoadOnce:
    """Singleton-like model wrapper"""
    _model = None

    model_dir = None

    def __init__(self):
        self.set_up()

    @classmethod
    def set_up(cls):
        model_path = settings.BASE_DIR.joinpath(f"id_service/trained_models/{cls.model_dir}")
        try:
            if cls._model is None:
                cls._model = load_model(model_path)
        except FileNotFoundError:
            raise ImproperlyConfigured(f"A model could not be found at {model_path}")


class Encoder(YouOnlyLoadOnce):
    model_dir = settings.ENCODER_DIR

    def predict(self,pixels:np.ndarray):
        """make sure to use inference.standardize_image to resize and obtain the pixels array before calling this"""
        try:
            assert len(pixels.shape) == 4
        except AssertionError:
            raise ValueError("input pixels should be a 4d array in the shape of batch, x, y, channel")
        # preprocess inputs then run inference
        embeddings = self._model.predict(preprocess_input(pixels))
        return embeddings


class Differentiator(YouOnlyLoadOnce):
    model_dir = settings.DIFFERENTIATOR_DIR

    def predict(self,batch_left, batch_right):
        if not isinstance(batch_left,np.ndarray):
            batch_left = np.array(batch_left)

        if not isinstance(batch_right,np.ndarray):
            batch_right = np.array(batch_right)

        if batch_left.shape != batch_right.shape:
            raise ValueError("Cannot compare unequal number of embeddings")

        # run input through model
        sameness = self._model.predict([batch_left,batch_right])

        # interpret result, need to decide on a threshold
        sameness_bool = np.greater_equal(sameness,np.full_like(sameness,fill_value=settings.SAMENESS_THRESHOLD))
        return sameness_bool


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


# force set up here
Encoder()
Differentiator()

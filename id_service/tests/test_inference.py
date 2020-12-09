from django.test import TestCase

from .__init__ import get_fake_image_file, get_test_embeddings
from ..inference import *


# note that the testcases here aren't django test cases
class TestImageUtil(TestCase):
    def setUp(self) -> None:

        self.original = get_fake_image_file()

    def test_standardize_image(self):

        # run image through
        new_image, pixels = standardize_image(self.original)

        self.assertTrue(isinstance(new_image,ImageFile))
        self.assertEqual(pixels.shape,(1,*settings.IMAGE_SIZE,3))


class TestMLModels(TestCase):

    def test_encoder(self):

        # get image, standardized
        new_image, pixels = standardize_image(get_fake_image_file())

        # do inference
        embedding = Encoder().predict(pixels)

        self.assertEqual(embedding.shape,(1, 4))

    def test_differ(self):

        # get a group of embeddings
        embeddings = get_test_embeddings()
        right = np.array([embeddings[0]for i in range(3)])
        left = np.array(embeddings[1:])

        sameness = Differentiator().predict(right,left)

        self.assertEqual(sameness.shape,(3,1))
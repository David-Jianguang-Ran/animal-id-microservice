from django.test import TestCase
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import InMemoryUploadedFile

from ..models import *

from PIL import Image
from io import BytesIO

import numpy as np
import random

COLLISION_TEST_COUNT = 10000


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


class TestRecordsBasic(TestCase):
    """
    This class tests basic record model creation,
    foreign key relationships,
    basically is here to catch syntax errors / refresh me on django
    """
    def test_image_record(self):

        # make image record
        image_1 = ImageRecord.objects.create()

        # test putting a file to it
        image_file = get_fake_image_file()
        image_1.file.save("test_file",image_file)

        # check if result has a url
        self.assertTrue(isinstance(image_1.file.url,str))

        # check if result can be found
        found = ImageRecord.objects.get(id=image_1.id)
        self.assertTrue(isinstance(found,ImageRecord))

        # check if relationship can be accessed
        self.assertIsNone(found.identity)
        self.assertIsNone(found.data_set)

    def test_image_vectors(self):
        # get mock image vectors
        embeddings = get_test_embeddings()
        ids = []

        # make image records and add embeddings
        for each_vector in embeddings:
            record = ImageRecord.objects.create()
            record.v0, record.v1, record.v2, record.v3 = each_vector
            ids.append(record.id)
            record.save()

    def test_animal_record(self):
        # create animal Record
        animal_1 = AnimalRecord.objects.create()

        # check if result can be found
        found = AnimalRecord.objects.get(id=animal_1.id)
        self.assertTrue(isinstance(found, AnimalRecord))

        # check relationships
        self.assertIsNone(found.data_set)
        self.assertEqual(len(found.images.all()), 0)

    def test_data_set(self):
        # can create
        d_set = DataSet.objects.create()

        # can be found
        found = DataSet.objects.get(id=d_set.id)
        self.assertTrue(isinstance(found,DataSet))

        # has relationships
        self.assertEqual(len(found.images.all()), 0)
        self.assertEqual(len(found.animals.all()), 0)


class TestAPIToken(TestCase):

    def test_creation(self):
        # create entry
        t = APIToken.objects.create()

        # find entry in db
        found = APIToken.objects.get(id=t.id)
        self.assertTrue(isinstance(found, APIToken))

        # check relationships
        self.assertIsNone(found.owner)
        self.assertIsNone(found.write_set)
        self.assertEqual(len(found.read_set.all()), 0)

    def test_collision(self):
        # make a bunch of tokens and store frequency in hash table
        known_id = {}
        for i in range(COLLISION_TEST_COUNT):
            entry = APIToken.objects.create()
            try:
                known_id[entry.id] += 1
            except KeyError:
                known_id[entry.id] = 1

        # check if there is at most 1 entry per id
        self.assertEqual(max(known_id.values()), 1)

    def test_validation_allowed(self):
        # first make a token
        t = APIToken.objects.create()

        # check if it is valid (it should be)
        self.assertTrue(t.valid_for_action)

        # set first use time to a few seconds ago
        t.first_use = datetime.now() - timedelta(hours=1)

        # check if it is valid
        self.assertTrue(t.valid_for_action)

    def test_validation_not_allowed(self):
        # make token, set time to an expired time
        t = APIToken.objects.create()
        t.first_use = datetime.now() - timedelta(days=settings.TOKEN_VALID_DAYS + 1)

        # check if it is invalid
        self.assertFalse(t.valid_for_action)

        # make another token, set time past but not expired
        t = APIToken.objects.create()
        past_sec = 1000
        t.first_use = datetime.now() - timedelta(seconds=past_sec)
        # set use count to exceeding allowed
        t.actions = past_sec * settings.MAX_ACTIONS_PER_SEC + 1

        # check if it is invalid
        self.assertFalse(t.valid_for_action)

        # simulate waiting 60 seconds
        t.first_use = t.first_use - timedelta(seconds=60)
        # now it should be valid again
        self.assertTrue(t.valid_for_action)


class TestModelInteractions(TestCase):

    @classmethod
    def setUpTestData(cls):
        # first create a default dataset
        # also remember the id of created objects
        cls.d_set = DataSet.objects.create()
        cls.known_images = []
        cls.known_animals = []

        # create some image records
        for i in range(100):
            img = ImageRecord.objects.create(data_set=cls.d_set)
            cls.known_images.append(img.id)

        # create animal records with associated images
        animal_holder = None
        for i in range(50):

            if i % 5 == 0:
                # create a new animal record
                animal_holder = AnimalRecord.objects.create(data_set=cls.d_set)
                cls.known_animals.append(animal_holder.id)

            img = ImageRecord.objects.create(data_set=cls.d_set,identity=animal_holder)
            cls.known_images.append(img.id)

    def test_filter_behaviour(self):
        pass

    def test_delete_behaviour(self):
        pass

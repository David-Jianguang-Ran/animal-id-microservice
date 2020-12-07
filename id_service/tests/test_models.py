from django.test import TestCase
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.exceptions import ObjectDoesNotExist

from .__init__ import get_fake_image_file, get_test_embeddings
from ..models import *

from PIL import Image
from io import BytesIO

import numpy as np
import random

COLLISION_TEST_COUNT = 10000





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
        image_1.image_file.save("test_file", image_file)

        # check if result has a url
        self.assertTrue(isinstance(image_1.image_file.url, str))

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
            ids.append(str(record.id))
            record.save()

        # try query by vector
        t0, t1, t2, t3 = embeddings[-1]
        found_set = ImageRecord.objects.filter(
            v0__range=(t0 - 10.0, t0 + 10.0),
            v1__range=(t1 - 10.0, t1 + 10.0),
            v2__range=(t2 - 10.0, t2 + 10.0),
            v3__range=(t3 - 10.0, t3 + 10.0),
        )

        # check of all but image 0 are in found set
        self.assertListEqual([each_id for each_id in found_set.values_list("id",flat=True)],ids[1:])


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
        self.assertTrue(t.is_valid(expensive=True))

        # set first use time to a little while ago
        t.first_use = datetime.now() - timedelta(hours=1)

        # check if it is valid
        self.assertTrue(t.is_valid(expensive=True))

    def test_validation_not_allowed(self):
        # make token, set time to an expired time
        t = APIToken.objects.create()
        t.first_use = datetime.now() - timedelta(days=settings.TOKEN_VALID_DAYS + 1)

        # check if it is invalid
        self.assertFalse(t.is_valid())

        # make another token, set time past but not expired
        t = APIToken.objects.create()
        past_sec = 1000
        t.first_use = datetime.now() - timedelta(seconds=past_sec)
        # set use count to exceeding allowed
        t.actions = past_sec * settings.MAX_ACTIONS_PER_SEC + 1

        # check if it is invalid
        self.assertFalse(t.is_valid())

        # simulate waiting 60 seconds
        t.first_use = t.first_use - timedelta(seconds=60)
        # now it should be valid again
        self.assertTrue(t.is_valid())


class TestModelInteractions(TestCase):

    @classmethod
    def setUpTestData(cls):
        # first create a default dataset
        # also remember the id of created objects
        cls.d_set = DataSet.objects.create()
        cls.known_images = []
        cls.known_animals = []

        # create some public image records
        for i in range(100):
            img = ImageRecord.objects.create()
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
        # records that belong in no data set can be found all the time
        # records the belong to a data set can only be found when a specific data set in mentioned

        # make a image with no d_set (public)
        img = ImageRecord.objects.create()

        # public image could be found without naming d_set
        try:
            found = ImageRecord.objects.filter(data_set__in=(self.d_set.id,),id=img.id).get()
        except ObjectDoesNotExist:
            found = ImageRecord.objects.filter(data_set=None,id=img.id).get()
        self.assertEqual(str(img.id),str(found.id))

        # private image cant be found if no d_set is named
        def do_search():
            return ImageRecord.objects.filter(data_set=None,id=self.known_images[-1]).get()
        self.assertRaises(ObjectDoesNotExist,do_search)

    # TODO : finish implementing below tests
    def test_delete_behaviour(self):
        pass

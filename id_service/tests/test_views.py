from django.test import TestCase, Client
from django.urls import reverse


from .__init__ import get_fake_image_file, get_test_embeddings
from ..models import DataSet, ImageRecord, AnimalRecord, APIToken, settings

class DBSetUpMixin:
    @classmethod
    def setUpTestData(cls):
        # create a default dataset
        # also remember the id of created objects
        cls.d_set = DataSet.objects.create()
        cls.known_images = []
        cls.known_animals = []

        # create some public image records
        for i in range(100):
            img = ImageRecord.objects.create()
            cls.known_images.append(str(img.id))

        # create animal records with associated images
        animal_holder = None
        for i in range(50):

            if i % 5 == 0:
                # create a new animal record
                animal_holder = AnimalRecord.objects.create(data_set=cls.d_set)
                cls.known_animals.append(str(animal_holder.id))

            img = ImageRecord.objects.create(data_set=cls.d_set,identity=animal_holder)
            cls.known_images.append(str(img.id))


class TestEndPoints(DBSetUpMixin, TestCase):
    # I know this test case is more like integrated test than unit test
    # oh well ~


    def setUp(self) -> None:
        # make a key
        key = APIToken.objects.create()
        key.read_set.add(self.d_set)
        key.write_set = self.d_set
        key.save()

        # create a test client
        self.client = Client(HTTP_X_API_KEY=key.id)

    def test_animal_query(self):
        # make a request with the key
        response = self.client.get(reverse("animal_endpoint",kwargs={"pk":self.known_animals[0]}))
        self.assertEqual(response.status_code, 200)

    def test_image_edit(self):
        # create record without image payload
        response = self.client.post(reverse("image_endpoint",kwargs={"pk":"new"}))
        self.assertEqual(response.status_code, 200)

        # creating record with anything other than POST isn't allowed
        response = self.client.delete(reverse("image_endpoint",kwargs={"pk":"new"}))
        self.assertEqual(response.status_code, 404)

        # create record with data
        with open(settings.BASE_DIR.joinpath("id_service/static/id_service/test_image.png"),"rb") as f:
            response = self.client.post(
                reverse("image_endpoint",kwargs={"pk":"new"}),
                {"data_set":str(self.d_set.id),"identity":self.known_animals[0],"image_file":f}
            )
        self.assertEqual(response.status_code, 200)
        found = ImageRecord.objects.get(id=response.json()['id'])
        self.assertTrue(isinstance(found,ImageRecord))

    def test_image_query(self):
        # test private image
        response = self.client.get(reverse("image_endpoint",kwargs={"pk":self.known_images[-2]}))
        self.assertEqual(response.status_code, 200)

        # test public image
        response = self.client.get(reverse("image_endpoint",kwargs={"pk":self.known_images[0]}))
        self.assertEqual(response.status_code, 200)

        # test delete private image
        response = self.client.delete(reverse("image_endpoint",kwargs={"pk":self.known_images[-1]}))
        self.assertEqual(response.status_code, 200)

    def test_dataset_query(self):
        # test viewing all animals in d_set
        response = self.client.get(reverse("data_set_endpoint",kwargs={"pk":str(self.d_set.id),"rel":"animals"}))
        self.assertEqual(response.status_code, 200)
        self.assertListEqual(response.json()["animals"],self.known_animals)

        # test viewing all images in d_set
        response = self.client.get(reverse("data_set_endpoint",kwargs={"pk":str(self.d_set.id),"rel":"images"}))
        self.assertEqual(response.status_code, 200)
        self.assertListEqual(response.json()["images"],self.known_images[100:])

        # test delete private d_set
        response = self.client.delete(reverse("data_set_endpoint",kwargs={"pk":str(self.d_set.id)}))
        self.assertEqual(response.status_code, 200)
        # check if the all images belong to d_set is gone
        self.assertEqual(len(ImageRecord.objects.all()),100)


class TestImageProcessing(DBSetUpMixin, TestCase):

    def setUp(self) -> None:

        # make a new token and d_set
        d_set = DataSet.objects.create()
        key = APIToken.objects.create(write_set=d_set)
        key.read_set.add(d_set)

        # create a test client
        self.client = Client(HTTP_X_API_KEY=key.id)

    def test_single_image_upload(self):

        for i in range(1,5):
            # create record with data
            with open(settings.BASE_DIR.joinpath(f"id_service/static/id_service/test_cat_{i}.png"), "rb") as f:
                response = self.client.post(
                    reverse("image_endpoint", kwargs={"pk": "new"}),
                    {"image_file": f}
                )
            self.assertEqual(response.status_code, 200)
            # check if a image record has been created
            found = ImageRecord.objects.get(id=response.json()['id'])
            self.assertTrue(isinstance(found, ImageRecord))
            # check if an identity has been created and linked
            found = AnimalRecord.objects.get(id=response.json()['identity'])
            self.assertTrue(isinstance(found, AnimalRecord))

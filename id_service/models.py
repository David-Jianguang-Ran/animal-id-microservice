from django.db import models
from django.conf import settings

from datetime import datetime, timedelta
from uuid import uuid4
# Create your models here.

# the fields are minimal on record related models, we only track id
# the idea is user services will keep their own db records,
# Auth user model is referenced here
# many DataSet to one User, related_name = data_sets
# many APIToken to one User, related_name = token


class DataSet(models.Model):
    id = models.CharField(primary_key=True,max_length=36,null=False,default=uuid4)
    name = models.CharField(max_length=64,blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,  # <= let's not delete entire database when users pack up and go home
        related_name="data_sets"
    )


class AnimalRecord(models.Model):
    # note animal id here is a uuid for consistency with rest of the models
    id = models.CharField(primary_key=True,max_length=36,null=False,default=uuid4)
    data_set = models.ForeignKey(DataSet,null=True,blank=True,on_delete=models.CASCADE,related_name="animals")


class ImageRecord(models.Model):
    id = models.CharField(primary_key=True,max_length=36,null=False,default=uuid4)
    data_set = models.ForeignKey(DataSet,null=True, blank=True,on_delete=models.CASCADE,related_name="images")

    # data related
    image_file = models.ImageField(upload_to="images", null=True, blank=True)  # <= TODO : upgrade to cloud storage backends when appropriate

    # vectorized image field
    # TODO : integrate postgres cube extension later
    v0 = models.FloatField(null=True)
    v1 = models.FloatField(null=True)
    v2 = models.FloatField(null=True)
    v3 = models.FloatField(null=True)

    identity = models.ForeignKey(AnimalRecord,null=True,blank=True,on_delete=models.CASCADE,related_name="images")

    @property
    def vector(self):
        return self.v0, self.v1, self.v2, self.v3

    @vector.setter
    def vector(self,vector_as_tuple):
        """NOTE: this setter does not call model.save()"""
        vector_as_tuple = [round(each,8)for each in vector_as_tuple]
        self.v0, self.v1, self.v2, self.v3 = vector_as_tuple

    @classmethod
    def vector_queryset(cls,vector,half_range=settings.SPACIAL_QUERY_DIST):
        """get a queryset filtered by proximity of model.vector to vector"""
        q0, q1, q2, q3 = vector
        return cls.objects.filter(
            v0__range=(q0 - half_range, q0 + half_range),
            v1__range=(q1 - half_range, q1 + half_range),
            v2__range=(q2 - half_range, q2 + half_range),
            v3__range=(q3 - half_range, q3 + half_range),
        )


class APIToken(models.Model):
    # TODO : find better secret generation and verification
    id = models.CharField(primary_key=True,max_length=36,null=False,default=uuid4)

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,  # <= let's not delete entire database when users pack up and go home
        related_name="tokens"
    )

    read_set = models.ManyToManyField(DataSet,related_name="+")
    write_set = models.ForeignKey(DataSet,related_name="+",null=True,on_delete=models.SET_NULL)

    created = models.DateTimeField(auto_now_add=True)
    first_use = models.DateTimeField(null=True)

    actions = models.IntegerField(default=0)
    expensive_actions = models.IntegerField(default=0)

    def is_valid(self, expensive=False):
        # resolve which field to check
        to_check = (self.expensive_actions, settings.MAX_EXPENSIVE_ACTIONS_PER_SEC) if expensive else (self.actions, settings.MAX_ACTIONS_PER_SEC)

        if self.first_use is None:
            return True
        elif self.first_use + timedelta(days=settings.TOKEN_VALID_DAYS) < datetime.now():
            # expired after too many days
            return False

        # users are allowed certain actions per second since the first use
        if to_check[0] < int((datetime.now() - self.first_use).total_seconds() * to_check[1]):
            return True
        else:
            return False

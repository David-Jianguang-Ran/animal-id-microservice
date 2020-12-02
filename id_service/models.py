from django.db import models
from django.conf import settings

from datetime import datetime, timedelta
from uuid import uuid4
# Create your models here.


# Auth user model is referenced here
# many DataSet to one User, related_name = data_sets
# many APIToken to one User, related_name = token


class DataSet(models.Model):
    id = models.CharField(primary_key=True,max_length=36,null=False,default=uuid4)
    name = models.CharField(max_length=64,null=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,  # <= let's not delete entire database when users pack up and go home
        related_name="data_sets"
    )


class AnimalRecord(models.Model):
    # note animal id here is a uuid for consistency with rest of the models
    id = models.CharField(primary_key=True,max_length=36,null=False,default=uuid4)
    name = models.CharField(max_length=64, null=True)
    data_set = models.ForeignKey(DataSet,null=True,on_delete=models.CASCADE,related_name="animals")


class ImageRecord(models.Model):
    id = models.CharField(primary_key=True,max_length=36,null=False,default=uuid4)
    data_set = models.ForeignKey(DataSet,null=True,on_delete=models.CASCADE,related_name="images")

    # data related
    file = models.ImageField(upload_to="images",null=True)  # <= TODO : upgrade to cloud storage backends when appropriate

    # vectorized image field
    # TODO : integrate postgres cube extension later
    v0 = models.DecimalField(max_digits=12,decimal_places=8,null=True)
    v1 = models.DecimalField(max_digits=12,decimal_places=8,null=True)
    v2 = models.DecimalField(max_digits=12,decimal_places=8,null=True)
    v3 = models.DecimalField(max_digits=12,decimal_places=8,null=True)

    identity = models.ForeignKey(AnimalRecord,null=True,on_delete=models.CASCADE,related_name="images")


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

    @property
    def valid_for_action(self):
        if self.first_use is None:
            return True
        elif self.first_use + timedelta(days=settings.TOKEN_VALID_DAYS) < datetime.now():
            # expired after too many days
            return False

        # users are allowed certain actions per second since the first use
        if self.actions < int((datetime.now() - self.first_use).total_seconds() * settings.MAX_ACTIONS_PER_SEC):
            return True
        else:
            return False

    # TODO : refactor repeated code
    @property
    def valid_for_expensive_action(self):
        if self.first_use is None:
            return True
        elif self.first_use + timedelta(days=settings.TOKEN_VALID_DAYS) < datetime.now():
            # expired after too many days
            return False

        # users are allowed certain actions per second since the first use
        if self.actions < int((datetime.now() - self.first_use).total_seconds() * settings.MAX_EXPENSIVE_ACTIONS_PER_SEC):
            return True
        else:
            return False

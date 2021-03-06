# Generated by Django 3.1.3 on 2020-12-02 17:06

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AnimalRecord',
            fields=[
                ('id', models.CharField(default=uuid.uuid4, max_length=36, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=64, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='DataSet',
            fields=[
                ('id', models.CharField(default=uuid.uuid4, max_length=36, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=64, null=True)),
                ('owner', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='data_sets', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='ImageRecord',
            fields=[
                ('id', models.CharField(default=uuid.uuid4, max_length=36, primary_key=True, serialize=False)),
                ('file', models.ImageField(null=True, upload_to='images')),
                ('v0', models.DecimalField(decimal_places=8, max_digits=12, null=True)),
                ('v1', models.DecimalField(decimal_places=8, max_digits=12, null=True)),
                ('v2', models.DecimalField(decimal_places=8, max_digits=12, null=True)),
                ('v3', models.DecimalField(decimal_places=8, max_digits=12, null=True)),
                ('data_set', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='images', to='id_service.dataset')),
                ('identity', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='images', to='id_service.animalrecord')),
            ],
        ),
        migrations.CreateModel(
            name='APIToken',
            fields=[
                ('id', models.CharField(default=uuid.uuid4, max_length=36, primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('first_use', models.DateTimeField(null=True)),
                ('actions', models.IntegerField(default=0)),
                ('expensive_actions', models.IntegerField(default=0)),
                ('owner', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tokens', to=settings.AUTH_USER_MODEL)),
                ('read_set', models.ManyToManyField(related_name='_apitoken_read_set_+', to='id_service.DataSet')),
                ('write_set', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='id_service.dataset')),
            ],
        ),
        migrations.AddField(
            model_name='animalrecord',
            name='data_set',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='animals', to='id_service.dataset'),
        ),
    ]

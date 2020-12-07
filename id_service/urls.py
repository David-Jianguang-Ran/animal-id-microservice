from django.urls import path

from .views import ImageView, AnimalView, DataSetView
from .views import get_documentation, get_about_me, get_demo_app, new_token, new_dataset

urlpatterns = [
    path("z/doc", get_documentation, name="documentation"),
    path("z/new_token", new_token, name="new_token"),
    path("z/new_set", new_dataset, name="new_dataset"),
    path("z/demo_app", get_demo_app, name="demo_app"),
    path("z/about", get_about_me, name="about_me"),
    # API endpoints
    path("image/<str:pk>", ImageView.as_view(), name="image_endpoint"),
    path("animal/<str:pk>", AnimalView.as_view(), name="animal_endpoint"),
    path("sets/<str:pk>", DataSetView.as_view(), name="data_set_endpoint"),
    path("sets/<str:pk>/<str:rel>", DataSetView.as_view(), name="data_set_endpoint")
]

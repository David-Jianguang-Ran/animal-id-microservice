from django.urls import path

from .views import ImageView, AnimalView, DataSetView

urlpatterns = [
    path("image/<str:pk>", ImageView.as_view(), name="image_endpoint"),
    path("animal/<str:pk>", AnimalView.as_view(), name="animal_endpoint"),
    path("sets/<str:pk>", DataSetView.as_view(), name="data_set_endpoint"),
    path("sets/<str:pk>/<str:rel>", DataSetView.as_view(), name="data_set_endpoint")
]
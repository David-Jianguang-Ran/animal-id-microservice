from django.shortcuts import render
from django.http import JsonResponse, FileResponse, HttpResponseBadRequest, HttpResponse
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied,RequestAborted
from django.views.generic.detail import BaseDetailView
from django.views.generic.list import BaseListView
from django.views.generic.edit import BaseUpdateView


from .models import ImageRecord, AnimalRecord, DataSet, APIToken


# OMG these views are such a crazy mess
def check_token(expensive_action=False):
    # this function can only decorate class based view methods!
    # needs APIMixin Class to work
    def __decorator(decoratee):

        def __inner(*args, **kwargs):
            view_instance = args[0]
            if view_instance.token.is_valid(expensive=expensive_action):
                # increment action counter
                if expensive_action:
                    view_instance.token.expensive_actions += 1
                else:
                    view_instance.token.actions += 1
                view_instance.token.save()

                return decoratee(*args, **kwargs)
            else:
                # TODO : add more helpful error message, make distinction between 429 and 403
                raise PermissionDenied

        return __inner

    return __decorator


class APIMixin:
    """Provides function for viewing, modifying model data via GET, DELETE """
    # needs these class attrs
    model = None

    def dispatch(self, request, *args, **kwargs):
        # first set up API token before calling super
        # now we can use @check token on http methods
        try:
            self.token = APIToken.objects.get(id=request.headers.get("x-api-key"))
        except APIToken.DoesNotExist:
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        # allow creation of records via POST
        if self.kwargs['pk'] == "new" and self.request.method == "POST":
            return self.model.objects.create()
        else:
            return super().get_object(queryset=queryset)

    def get_queryset(self):
        # first get q_set normally
        q_set = super().get_queryset()
        # filter by token read_set field
        # make the queryset
        if len(self.token.read_set.all()) == 0:
            # public token, show only public data (dataset is None)
            return q_set.filter(data_set=None)
        else:
            # search both any named private and public set
            return q_set.filter(data_set=None) | \
                   q_set.filter(data_set__in=(self.token.read_set.values_list("id",flat=True)))

    # http methods
    @check_token(expensive_action=True)
    def delete(self, request, *args, **kwargs):
        # being able to get object means object exist and token has the matching d_set
        self.object = self.get_object()
        self.object.delete()
        return HttpResponse("")


class RelatedListMixin:
    """Provides functionality for viewing model and related foreign key objects via GET"""
    related_name = None

    def get_queryset(self):
        try:
            # save base object
            self.object = self.get_object()
            return getattr(self.object, self.related_name).all().order_by("data_set")

        except (ObjectDoesNotExist, AttributeError):
            raise RequestAborted

    def get_object(self, queryset=None):
        # allow creation of records via POST
        if self.kwargs['pk'] == "new" and self.request.method == "POST":
            return self.model.objects.create()
        else:
            return self.model.objects.get(pk=self.kwargs["pk"])

    def render_to_response(self,context):
        json_response = {
            "type" : self.model.__name__,
            "id" : self.object.id,
            "data_set": None if self.object.data_set is None else self.object.data_set.id,
            self.related_name : list(context['object_list'].values_list("id", flat=True)),
        }
        return JsonResponse(json_response)


class ImageView(APIMixin, BaseDetailView, BaseUpdateView):
    """end point for getting json data, posting form/ files, and deleting images"""
    model = ImageRecord
    fields = ["data_set",'image_file','identity']

    @check_token()
    def get(self, request, *args, **kwargs):
        return super(ImageView, self).get(request, *args, **kwargs)

    @check_token()
    def post(self, request, *args, **kwargs):
        return super(ImageView, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        # this is where we call encoder
        res = super(ImageView, self).form_valid(form=form)

    def render_to_response(self,context):
        json_response = {
            "type" : "ImageRecord",
            "id" : context['object'].id,
            "data_set": None if context['object'].data_set is None else context['object'].data_set.id,
            "identity": None if context['object'].identity is None else context['object'].identity.id,
        }
        # image file may not exist
        try:
            json_response["image_url"] = self.object.image_file.url
        except ValueError:
            json_response["image_url"] = None

        return JsonResponse(json_response)


class AnimalView(RelatedListMixin, APIMixin, BaseListView):
    """serves animal record with related images, supports pagination?"""
    model = AnimalRecord
    related_name = "images"
    paginate_by = 32

    @check_token()
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class DataSetView(RelatedListMixin, APIMixin, BaseListView, BaseUpdateView):
    """serves dataset record, optional url arg for dumping out all images or animals"""
    model = DataSet
    related_name = None
    fields = ['name', 'owner']

    paginate_by = 64

    @check_token(expensive_action=True)
    def get(self, request, *args, **kwargs):
        # in case rel is not captured from url, just do a json response for object
        try:
            self.related_name = self.kwargs['rel']
            return super(DataSetView, self).get(request, *args, **kwargs)
        except KeyError:
            self.object = self.get_object()
            return self.render_to_response(context={'object_list':None})

    @check_token()
    def post(self, request, *args, **kwargs):
        return super(DataSetView, self).post(request, *args, **kwargs)

    def render_to_response(self, context):
        json_response = {
            "type": self.model.__name__,
            "id": self.object.id,
            "name":self.object.name,
            "owner": None if self.object.owner is None else self.object.owner.id,
        }
        # may not need a related object list
        if context['object_list']:
            json_response[self.related_name] = list(context['object_list'].values_list("id", flat=True))

        return JsonResponse(json_response)







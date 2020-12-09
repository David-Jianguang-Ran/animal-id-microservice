from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied,RequestAborted
from django.core.files.images import ImageFile
from django.http import Http404, JsonResponse, FileResponse, HttpResponseBadRequest, HttpResponse
from django.views.generic.base import View
from django.views.generic.edit import model_forms
from django.views.generic.list import MultipleObjectMixin
from django.db.models import Model


from .models import ImageRecord, AnimalRecord, DataSet, APIToken
from .inference import standardize_image, Encoder, Differentiator


###
## API Views
#
def check_token(expensive_action=False):
    """
    this function can only decorate class based view methods! 
    needs UnifiedBase Class to work
    """
    def __decorator(decoratee):

        def __inner(*args, **kwargs):
            view_instance = args[0]
            if view_instance.token.is_valid(expensive=expensive_action):
                # increment action counter
                if expensive_action:
                    view_instance.token.expensive_actions += 1
                else:
                    view_instance.token.actions += 1

                # save token after view has returned, so we can increment expensive counters later on
                return decoratee(*args, **kwargs)

            else:
                # TODO : add more helpful error message, make distinction between 429 and 403
                raise PermissionDenied

        return __inner

    return __decorator


class UnifiedBase(View):
    """
    This class provides functionality for read, update, create, delete model and possible related model lists  
    This view requires header x-api-key to be set to a valid API token obtained in another view  
    The read_set and write_set attribute of APIToken also controlls read write permissions  
    
    call flow for handling requests:
    1. setup  
    1. dispatch  
    1. get_or_create_object  
    1. django.View.dispatch => get or post or delete  
    1. (optional, using related model list) get_related  
    1. self.object.save and self.token.save
    1. json_response
    ideally methods doesn't return anything but rather modify view instance attributes
    
    To use:
    -subclass this view
    -implement GET POST or DELETE handlers, note the handlers can just return True for a json response  
    -(optional) use check_token to decorate views for rate limiting  
    -(optional) in order to return related model lists, either:  
    define defualt_related_names in class declearation _OR_ 
    include an kwrard argument rel in url routing 
    """
    model = None  # <= django model class
    default_related_names = []  # <= related name of foreign key fields
    fields = []  # <= read/write access to model fields

    def setup(self, request, *args, **kwargs):
        # setting up super class
        super(UnifiedBase, self).setup(request, *args, **kwargs)

        # ensure we have a valid token attached to request
        try:
            self.token = APIToken.objects.get(id=request.headers.get("x-api-key"))
        except APIToken.DoesNotExist:
            raise PermissionDenied

        if not self.token.is_valid():
            raise PermissionDenied

        # if a related model is named in kwargs, record that name for later
        self.related_names = []
        if len(self.default_related_names) != 0:
            self.related_names += self.default_related_names
        try:
            self.related_names += self.kwargs['rel'] if not isinstance(self.kwargs['rel'],str) else [self.kwargs["rel"]]
        except KeyError:
            pass

    def filter_by_token(self, queryset):
        if len(self.token.read_set.all()) == 0:
            return queryset.filter(data_set=None)
        else:
            return queryset.filter(data_set=None) | \
                   queryset.filter(data_set__in=self.token.read_set.all().values_list("id",flat=True))

    def get_or_create_object(self):
        # get object or create new
        try:
            filtered = self.filter_by_token(self.model.objects.filter(pk=self.kwargs['pk']))
            self.object = filtered.get()
        except self.model.DoesNotExist:
            if self.request.method == "POST" and self.kwargs["pk"] == "new":
                self.object = self.model.objects.create(data_set=self.token.write_set)
            else:
                raise Http404

    def get_related(self):
        self.related = {}
        for each_name in self.related_names:
            try:
                # get a q_set
                related_set = getattr(self.object,each_name)
                # filter it
                self.related[each_name] = self.filter_by_token(related_set)
            except AttributeError:
                pass

    def get_form(self,request):
        # get a model form, fill it with data
        # to be used in POST
        return model_forms.modelform_factory(self.model,fields=self.fields)(data=self.request.POST,files=self.request.FILES)

    def json_response(self):
        # dump out basic fields, always include id
        to_json = {"model":self.model.__name__}
        for each in ["id"] + self.fields:
            value = getattr(self.object,each,None)
            # serialize model by id
            if isinstance(value,Model):
                value = str(value.id)
            # serialize file by url
            if isinstance(value,ImageFile):
                try:
                    value = value.url
                except ValueError:
                    value = None

            to_json[each] = value

        # dump out related fields
        for name, each_set in self.related.items():
            to_json[name] = list(each_set.values_list("id",flat=True))
        return JsonResponse(to_json)

    def dispatch(self, request, *args, **kwargs):
        # setting up data first before dispatching to HTTP methods
        self.get_or_create_object()

        # so our views don't really need to return a http response,
        # since most likely we'll want a json response with object data
        ok = super(UnifiedBase, self).dispatch(request,*args,**kwargs)

        if ok is True:
            # save object
            self.object.save()
            # save token
            self.token.save()
            # getting related data if any for response
            self.get_related()
            return self.json_response()
        elif isinstance(ok,HttpResponse):
            return ok
        else:
            return HttpResponseBadRequest()

    # GET and Delete are always available
    @check_token()
    def get(self,request,*args,**kwargs):
        # no need to do anything in HTTP GET
        # getting db model object and returning JSON is always done if we return True Here
        return True

    @check_token(expensive_action=True)  # <= it's not really expensive, we just don't like it when users delete stuff
    def delete(self,request,*args,**kwargs):
        # only non-public data can be deleted with the right key
        if self.object.data_set is not None and self.object.data_set == self.token.write_set:
            # have to return a http 200 here instead of object data
            self.object.delete()
            return HttpResponse("OK")
        else:
            raise PermissionDenied


class ImageView(UnifiedBase):
    """
    Main endpoint for ImageRecord model,  
    image upload handling and inference happens here too  
    """
    model = ImageRecord
    fields = ["data_set","image_file","identity"]

    @check_token()
    def post(self,request,*args,**kwargs):
        # HTTP POST needs to do its own data modification, (basically just a form_valid)
        populated_form = self.get_form(request=request)

        # only save form when data is valid
        if populated_form.is_valid():
            self.object = populated_form.save(commit=False)

            # TODO : validate image and call image encoder here
            try:
                cleaned_image, embedding_vector = self.process_image(populated_form.files["image_file"])
                embedding_vector = list(embedding_vector[0])
                # update object with computed image related data
                self.object.image_file = cleaned_image
                self.object.vector = embedding_vector

                # if an identity isn't provided, make new or find matching one
                if self.object.identity is None:
                    self.object.identity = self.get_identity(embedding_vector)

            except KeyError:
                # No image is uploaded, no ML inference
                pass

        # new records have empty forms, but still it's not a bad request
        elif self.kwargs['pk'] != "new":
            return False

        return True

    @check_token(expensive_action=True)
    def process_image(self,image_file):
        """
        returns a cleaned, standard sized django ImageFile, and embedding vector of image
        """
        # resize image
        new_file, pixels = standardize_image(image_file)

        # run pixels through encoder
        vector = Encoder().predict(pixels)
        vector = list(vector)

        return new_file, vector

    @check_token(expensive_action=True)
    def get_identity(self,vector):
        # query db by vector proximity
        same_set = ImageRecord.vector_queryset(vector)

        # bail early and create new id if nothing came back from db
        if len(same_set) == 0:
            new_animal = AnimalRecord.objects.create(data_set=self.token.write_set)
            return new_animal

        #  verify each possible candidate
        compare_left = [each_record.vector for each_record in same_set]
        compare_right = [vector for each in compare_left]
        sameness = Differentiator().predict(compare_left,compare_right)

        # decode and find animal id
        # write identity to object
        possible_ids = {}

        for is_same, animal_id in zip(list(sameness),same_set.values_list("identity_id",flat=True)):
            # tally each hit in identity/sameness
            if is_same:
                try:
                    possible_ids[str(animal_id)] += 1
                except KeyError:
                    possible_ids[str(animal_id)] = 1

        # if none are found, make new id
        if len(possible_ids) == 0:
            new_animal = AnimalRecord.objects.create(data_set=self.token.write_set)
            return new_animal
        else:
            # take highest count, assign image to that animal
            ranked = sorted(possible_ids.items(),key=lambda x:x[1],reverse=True)

            found_animal = AnimalRecord.objects.get(id=ranked[0][0])
            return found_animal


class AnimalView(UnifiedBase):
    """update by user is not allowed, animal identities are generated by ML system"""
    model = AnimalRecord
    default_related_names = ["images"]
    fields = ["data_set"]


class DataSetView(UnifiedBase):
    """Main endpoint for DataSet model used in access control."""
    model = DataSet
    fields = ["name","owner"]

    def filter_by_token(self, queryset):
        # filtering by d_set too, only token associated to d_set can see this one
        if queryset.model == DataSet:
            return queryset.filter(id__in=self.token.read_set.all().values_list("id",flat=True))
        else:
            return super(DataSetView, self).filter_by_token(queryset=queryset)

    @check_token(expensive_action=True)  # <= it's not really expensive, we just don't like it when users delete stuff
    def delete(self, request, *args, **kwargs):
        # only non-public data can be deleted with the right key
        if self.object == self.token.write_set:
            # have to return a http 200 here instead of object data
            self.object.delete()
            return HttpResponse("OK")
        else:
            raise PermissionDenied

# TODO : finish static and management views

###
## Management Views
#
def get_documentation(request):
    pass


def new_token(request):
    pass


@login_required()
def get_status(request):
    pass


@login_required()
def new_dataset(request):
    pass


###
## Bonus / About Me pages
#

def get_about_me(request):
    pass


def get_demo_app(request):
    pass


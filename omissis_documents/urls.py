from django.urls import path, re_path
from . import views


app_name = "omissis_documents"


urlpatterns = [
    path("", views.upload_documento, name="upload"),
]
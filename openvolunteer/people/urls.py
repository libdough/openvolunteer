from django.urls import path

from . import views

app_name = "people"

urlpatterns = [
    path("", views.person_list, name="person_list"),
    path("new/", views.person_form, name="person_create"),
    path("<uuid:person_id>/", views.person_detail, name="person_detail"),
    path(
        "<uuid:person_id>/edit/",
        views.person_form,
        name="person_edit",
    ),
    path("upload/", views.person_upload_csv, name="person_upload"),
    path("search/", views.person_search, name="person_search"),
]

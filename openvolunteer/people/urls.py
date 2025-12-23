from django.urls import path

from . import views

app_name = "people"

urlpatterns = [
    path("people/", views.person_list, name="person_list"),
    path("people/new/", views.person_create, name="person_create"),
    path("people/<uuid:person_id>/", views.person_detail, name="person_detail"),
]

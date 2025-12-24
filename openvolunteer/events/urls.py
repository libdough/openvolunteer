from django.urls import path

from . import views

app_name = "events"

urlpatterns = [
    path("", views.event_list, name="event_list"),
    path("<uuid:event_id>/", views.event_detail, name="event_detail"),
    path(
        "shifts/<uuid:shift_id>/signup/",
        views.shift_assign_people,
        name="shift_assign_people",
    ),
]

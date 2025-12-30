from django.urls import path

from . import views

app_name = "events"

urlpatterns = [
    path("", views.event_list, name="event_list"),
    path("<uuid:event_id>/", views.event_detail, name="event_detail"),
    path("new/", views.event_create, name="event_create"),
    path("<uuid:event_id>/edit/", views.event_edit, name="event_edit"),
    path(
        "shifts/<uuid:shift_id>/signup/",
        views.shift_assign_people,
        name="shift_assign_people",
    ),
    path(
        "<uuid:event_id>/update-times/",
        views.event_update_times,
        name="event_update_times",
    ),
    # Calendars
    path(
        "calendar/",
        views.calendar_events,
        name="calendar",
    ),
]

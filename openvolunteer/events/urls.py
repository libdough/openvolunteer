from django.urls import path

from . import views

app_name = "events"

urlpatterns = [
    path("", views.EventListView.as_view(), name="event_list"),
    path("<uuid:pk>/", views.EventDetailView.as_view(), name="event_detail"),
    path(
        "shifts/<uuid:shift_id>/signup/",
        views.shift_signup,
        name="shift_signup",
    ),
]

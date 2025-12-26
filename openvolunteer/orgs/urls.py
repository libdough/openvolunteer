from django.urls import path

from . import views

app_name = "orgs"

urlpatterns = [
    path("", views.org_list, name="org_list"),
    path("create/", views.org_create, name="org_create"),
    path("<slug:slug>/", views.org_detail, name="org_detail"),
    path("<slug:slug>/edit/", views.org_edit, name="org_edit"),
    path("<slug:slug>/members/", views.org_members, name="org_members"),
    path(
        "<slug:slug>/members/<uuid:member_id>/update/",
        views.org_member_update,
        name="org_member_update",
    ),
    path(
        "<slug:slug>/members/<uuid:member_id>/remove/",
        views.org_member_remove,
        name="org_member_remove",
    ),
    path("orgs/<slug:slug>/people/", views.org_people, name="org_people"),
    # Calendars
    path(
        "<slug:slug>/calendar/",
        views.org_calendar,
        name="org_calendar",
    ),
    path(
        "<slug:slug>/calendar/events/",
        views.org_calendar_events,
        name="org_calendar_events",
    ),
]

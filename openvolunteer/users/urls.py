#!/usr/bin/env python3
from django.urls import path

from .views import user_detail_view
from .views import user_redirect_view
from .views import user_search
from .views import user_update_view

app_name = "users"
urlpatterns = [
    path("api/search/", view=user_search, name="user_search"),
    path("~redirect/", view=user_redirect_view, name="redirect"),
    path("~update/", view=user_update_view, name="update"),
    path("<str:username>/", view=user_detail_view, name="detail"),
]

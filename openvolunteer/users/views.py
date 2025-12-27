#!/usr/bin/env python3
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.db.models import QuerySet
from django.http import JsonResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView
from django.views.generic import RedirectView
from django.views.generic import UpdateView

from openvolunteer.users.models import User


class UserDetailView(LoginRequiredMixin, DetailView):
    model = User
    slug_field = "username"
    slug_url_kwarg = "username"


user_detail_view = UserDetailView.as_view()


class UserUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = User
    fields = ["name"]
    success_message = _("Information successfully updated")

    def get_success_url(self) -> str:
        assert self.request.user.is_authenticated  # type guard
        return self.request.user.get_absolute_url()

    def get_object(self, queryset: QuerySet | None = None) -> User:
        assert self.request.user.is_authenticated  # type guard
        return self.request.user


user_update_view = UserUpdateView.as_view()


class UserRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self) -> str:
        return reverse("users:detail", kwargs={"username": self.request.user.username})


user_redirect_view = UserRedirectView.as_view()

MIN_SEARCH_QUERY_LEN = 2


@login_required
def user_search(request):
    """
    Search users by name / email / username.
    Intended for admin/org-admin use.
    """
    # TODO: limit user search permissions
    if not (request.user.is_staff or request.user.is_superuser):
        msg = "You do not have permission to search users"
        raise PermissionDenied(msg)
    q = request.GET.get("q", "").strip()

    if len(q) < MIN_SEARCH_QUERY_LEN:
        return JsonResponse({"results": []})

    users = User.objects.filter(
        Q(id__icontains=q) | Q(email__icontains=q) | Q(username__icontains=q),
        # | Q(first_name__icontains=q)
        # | Q(last_name__icontains=q)
    ).order_by("id")[:10]

    return JsonResponse(
        {
            "results": [
                {
                    "id": str(user.id),
                    "email": user.email
                    if (request.user.is_staff or request.is_superuser)
                    else "<hidden>",
                    "username": user.username,
                    "name": user.get_full_name() or user.username,
                }
                for user in users
            ],
        },
    )

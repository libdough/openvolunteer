from django.urls import path

from . import views

app_name = "tickets"

urlpatterns = [
    path("", views.ticket_list, name="ticket_list"),
    path("<uuid:ticket_id>/", views.ticket_detail, name="ticket_detail"),
    path("<uuid:ticket_id>/claim/", views.claim_ticket, name="claim_ticket"),
    path("<uuid:ticket_id>/unclaim/", views.unclaim_ticket, name="unclaim_ticket"),
    path("<uuid:ticket_id>/update/", views.update_ticket, name="update_ticket"),
]

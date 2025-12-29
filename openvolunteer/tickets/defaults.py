import json

from django_celery_beat.models import CrontabSchedule
from django_celery_beat.models import IntervalSchedule
from django_celery_beat.models import PeriodicTask

from openvolunteer.events.models import EventTemplate
from openvolunteer.events.models import ShiftAssignmentStatus

from .actions.enum import TicketActionRunWhen
from .actions.models import TicketActionButtonColor
from .actions.models import TicketActionTemplate
from .actions.models import TicketActionType
from .models import TicketStatus
from .models import TicketTemplate


def install_default_ticket_actions():
    """
    Install global TicketActionTemplates.
    """
    initialize_assignment, _ = TicketActionTemplate.objects.get_or_create(
        slug="initialize_assignment",
        action_type=TicketActionType.UPDATE_SHIFT_STATUS,
        label="Initialize Assignment",
        defaults={
            "run_when": TicketActionRunWhen.ON_CREATE,
            "description": (
                "Can be run on ticket creation to change the "
                "status of a new assignment from init to pending"
            ),
            "button_color": TicketActionButtonColor.SECONDARY,
            "config": {
                "status": ShiftAssignmentStatus.PENDING,
            },
        },
    )

    mark_introduced, _ = TicketActionTemplate.objects.get_or_create(
        slug="mark_introduced",
        action_type=TicketActionType.REMOVE_TAG,
        label="Mark Person as Introduced",
        defaults={
            "run_when": TicketActionRunWhen.MANUAL,
            "description": (
                "This person was unintroduced to the organization "
                "this action marks that we have now said hello"
            ),
            "button_color": TicketActionButtonColor.PRIMARY,
            "config": {
                "tag": "unintroduced",
            },
        },
    )

    mark_interest_phone_banking, _ = TicketActionTemplate.objects.get_or_create(
        slug="mark_interest_phone_banking",
        action_type=TicketActionType.UPSERT_TAG,
        label="Interest Phone Banking",
        defaults={
            "run_when": TicketActionRunWhen.MANUAL,
            "description": ("Mark this person as interested in phone banking"),
            "button_color": TicketActionButtonColor.SECONDARY,
            "config": {
                "tag": "phonebank",
            },
        },
    )

    mark_interest_canvassing, _ = TicketActionTemplate.objects.get_or_create(
        slug="mark_interest_canvassing",
        action_type=TicketActionType.UPSERT_TAG,
        label="Interest Phone Banking",
        defaults={
            "run_when": TicketActionRunWhen.MANUAL,
            "description": ("Mark this person as interested in canvassing"),
            "button_color": TicketActionButtonColor.SECONDARY,
            "config": {
                "tag": "canvasser",
            },
        },
    )

    mark_do_not_contact, _ = TicketActionTemplate.objects.get_or_create(
        slug="mark_do_not_contact",
        action_type=TicketActionType.UPSERT_TAG,
        label="Mark Do Not Contact",
        defaults={
            "run_when": TicketActionRunWhen.MANUAL,
            "description": ("Marks this person as someone not to contact"),
            "button_color": TicketActionButtonColor.DANGER,
            "config": {
                "tag": "No Contact",
            },
        },
    )

    create_assignment, _ = TicketActionTemplate.objects.get_or_create(
        slug="create_assignment",
        action_type=TicketActionType.UPSERT_SHIFT_ASSIGNMENT,
        label="Confirm Interest",
        defaults={
            "description": (
                "Confirms that the person is interested and creates an event "
                "assignment with a fully committed status. "
                "This action also marks the ticket as completed."
            ),
            "button_color": TicketActionButtonColor.PRIMARY,
            "config": {
                "status": ShiftAssignmentStatus.CONFIRMED,
            },
            "updates_ticket_status": TicketStatus.COMPLETED,
        },
    )

    create_assignment_partial, _ = TicketActionTemplate.objects.get_or_create(
        slug="create_assignment_partial",
        action_type=TicketActionType.UPSERT_SHIFT_ASSIGNMENT,
        label="Maybe",
        defaults={
            "description": (
                "Creates an event assignment indicating partial or tentative "
                "interest from the person. "
                "Use this when the person is unsure or only partially available."
            ),
            "button_color": TicketActionButtonColor.SECONDARY,
            "config": {
                "status": ShiftAssignmentStatus.PARTIAL,
            },
            "updates_ticket_status": TicketStatus.COMPLETED,
        },
    )

    complete_ticket, _ = TicketActionTemplate.objects.get_or_create(
        slug="complete_ticket",
        action_type=TicketActionType.NOOP,
        label="Completed",
        defaults={
            "description": (
                "Marks the ticket as completed without performing any "
                "additional actions. "
                "Useful when the task has been finished manually."
            ),
            "button_color": TicketActionButtonColor.PRIMARY,
            "updates_ticket_status": TicketStatus.COMPLETED,
        },
    )

    block_ticket, _ = TicketActionTemplate.objects.get_or_create(
        slug="block_ticket",
        action_type=TicketActionType.NOOP,
        label="Block Ticket",
        defaults={
            "description": ("Marks this ticket as blocked"),
            "button_color": TicketActionButtonColor.WARNING,
            "updates_ticket_status": TicketStatus.BLOCKED,
        },
    )

    close_ticket, _ = TicketActionTemplate.objects.get_or_create(
        slug="close_ticket",
        action_type=TicketActionType.NOOP,
        label="Close Ticket",
        defaults={
            "description": (
                "Closes the ticket without taking further action. "
                "Use this when the ticket is no longer relevant or should not "
                "be acted upon."
            ),
            "button_color": TicketActionButtonColor.DANGER,
            "updates_ticket_status": TicketStatus.COMPLETED,
        },
    )

    update_assignment_confirm, _ = TicketActionTemplate.objects.get_or_create(
        slug="update_assignment_confirm",
        action_type=TicketActionType.UPDATE_SHIFT_STATUS,
        label="Confirmed",
        defaults={
            "description": (
                "Updates the existing event assignment to indicate the person "
                "is fully committed. "
                "This action is useful when confirming participation."
            ),
            "button_color": TicketActionButtonColor.PRIMARY,
            "config": {
                "status": ShiftAssignmentStatus.CONFIRMED,
            },
            "updates_ticket_status": TicketStatus.COMPLETED,
        },
    )

    update_assignment_rejected, _ = TicketActionTemplate.objects.get_or_create(
        slug="update_assignment_rejected",
        action_type=TicketActionType.UPDATE_SHIFT_STATUS,
        label="Not Interested",
        defaults={
            "description": (
                "Updates the shift assignment to indicate the person is no longer "
                "interested or has declined to participate."
            ),
            "button_color": TicketActionButtonColor.DANGER,
            "config": {
                "status": ShiftAssignmentStatus.DECLINED,
            },
            "updates_ticket_status": TicketStatus.COMPLETED,
        },
    )

    return {
        "initialize_assignment": initialize_assignment,
        "create_assignment": create_assignment,
        "create_assignment_partial": create_assignment_partial,
        "mark_introduced": mark_introduced,
        "mark_interest_phone_banking": mark_interest_phone_banking,
        "mark_interest_canvassing": mark_interest_canvassing,
        "mark_do_not_contact": mark_do_not_contact,
        "complete_ticket": complete_ticket,
        "block_ticket": block_ticket,
        "close_ticket": close_ticket,
        "update_assignment_confirm": update_assignment_confirm,
        "update_assignment_rejected": update_assignment_rejected,
    }


def install_default_ticket_templates(actions):
    """
    Install global TicketTemplates.
    """

    introduction, created = TicketTemplate.objects.get_or_create(
        name="Introduction",
        defaults={
            "ticket_name_template": "Introduce yourself to {{person.discord}}",
            "description_template": (
                "1. Mark ticket as in progress\n"
                "\n"
                "2. Find {{person.discord}} on discord.\n"
                "\n"
                "3. Copy the below text into a DM for {{person.discord}}\n"
                "\n"
                "```copy\n"
                "Hi {{person.discord}},\n"
                "\n"
                "We noticed you joined the discord.\n"
                "\n"
                "We're happy you are here! We wanted to know if you were interested "
                "getting more involved? We have a few activities "
                "that you might like:\n\n"
                "1. Phone Banking\n"
                "2. Canvassing\n"
                "\n"
                "Please let us know if you are interested!\n"
                "```\n"
                "\n"
                "4. Mark them as introduced using the action on this ticket.\n"
                "\n"
                "5. Await their response. Feel free to claim other tickets while "
                "you wait.\n"
                "\n"
                "6. If they confirm their interest in the activities click the "
                " corresponding action button. \n"
                "If they are not interested, click the `close ticket` action button."
                "\n"
                "7. If they are hostile or expressly do not wish to be contacted, "
                "click the `mark do not contact` and then close the ticket."
            ),
            "default_priority": 3,
            "claimable": True,
        },
    )
    if created:
        introduction.action_templates.set(
            [
                actions["mark_introduced"],
                actions["mark_interest_phone_banking"],
                actions["mark_interest_canvassing"],
                actions["close_ticket"],
                actions["mark_do_not_contact"],
            ],
        )

    recruit, created = TicketTemplate.objects.get_or_create(
        name="Recruit for Event",
        defaults={
            "ticket_name_template": "Recruit {{person.discord}} for {{event_title}}",
            "description_template": (
                "1. Mark ticket as in progress\n"
                "\n"
                "2. Find {{person.discord}} on discord.\n"
                "\n"
                "3. Copy the below text into a DM for {{person.discord}}\n"
                "\n"
                "```copy\n"
                "Hi {{person.discord}},\n"
                "\n"
                "It is very important that we all put in the "
                "effort to make a difference.\n"
                "\n"
                "Would you be interested in volunteering for "
                "{{event_type}} on {{event_starts_at.date.est}} "
                "at {{event_starts_at.time.est}}?\n"
                "\n"
                "Please let us know!\n"
                "```\n"
                "\n"
                "4. Await their response\n"
                "\n"
                "5. If they confirm their interest, click the `confirm` action button. "
                "If they are not interested, click the `reject` action button.\n"
            ),
            "default_priority": 3,
            "claimable": True,
        },
    )
    if created:
        recruit.action_templates.set(
            [
                actions["initialize_assignment"],
                actions["create_assignment"],
                actions["create_assignment_partial"],
                actions["update_assignment_rejected"],
            ],
        )

    reconfirmation, created = TicketTemplate.objects.get_or_create(
        name="Reconfirmation",
        defaults={
            "ticket_name_template": "Reconfirm {{person.discord}} for {{event.name}}",
            "description_template": (
                "Hi {{person.discord}}!\n"
                "Please reconfirm your availability for "
                "**{{ event.name }}** on {{ event_starts_at.est }}.\n"
                "See You soon!"
            ),
            "default_priority": 4,
            "claimable": True,
        },
    )
    if created:
        reconfirmation.action_templates.set(
            [
                actions["update_assignment_confirm"],
                actions["update_assignment_rejected"],
            ],
        )

    handout_phone_banks, created = TicketTemplate.objects.get_or_create(
        name="Handout Phone Banks",
        defaults={
            "ticket_name_template": "Distribute phone numbers to {{person.discord}}",
            "description_template": (
                "Distribute phone bank materials for "
                "**{{ event.name }}**. \n\n"
                "Please contact {{event.owned_by}} for more details."
            ),
            "default_priority": 2,
            "claimable": False,
        },
    )
    if created:
        handout_phone_banks.action_templates.set(
            [actions["complete_ticket"], actions["close_ticket"]],
        )

    return {
        "introduction": introduction,
        "recruit": recruit,
        "reconfirmation": reconfirmation,
        "handout_phone_banks": handout_phone_banks,
    }


def install_default_event_templates(ticket_templates):
    """
    Install global EventTemplates and attach TicketTemplates.
    """

    event_template_defs = {
        "Canvass": [
            ticket_templates["recruit"],
            ticket_templates["reconfirmation"],
        ],
        "Phone Bank": [
            ticket_templates["recruit"],
            ticket_templates["handout_phone_banks"],
        ],
        "Meetup": [
            ticket_templates["recruit"],
        ],
        "Training": [
            ticket_templates["recruit"],
        ],
    }

    for name, tickets in event_template_defs.items():
        event_template, _ = EventTemplate.objects.get_or_create(
            name=name,
            defaults={},
        )

        event_template.ticket_templates.set(tickets)


def install_default_tasks():
    every_fifteen_minutes, _ = IntervalSchedule.objects.get_or_create(
        every=15,
        period=IntervalSchedule.MINUTES,
    )

    create_intro_tix, _ = PeriodicTask.objects.get_or_create(
        name="Create intro tickets for unintroduced people",
        defaults={
            "task": "openvolunteer.tickets.tasks.create_tickets_for_people_with_tag",
            "interval": every_fifteen_minutes,
            "kwargs": json.dumps(
                {
                    "template_name": "Introduction",
                    "tag_name": "unintroduced",
                },
            ),
            "enabled": True,
            "description": (
                "Create introduction tickets for "
                "those that have not yet been introduced"
            ),
        },
    )

    midnight, _ = CrontabSchedule.objects.get_or_create(
        minute="0",
        hour="5",
        day_of_week="*",
        day_of_month="*",
        month_of_year="*",
        timezone="UTC",
    )

    cancel_stale_tix = PeriodicTask.objects.get_or_create(
        name="Cancel stale tickets",
        defaults={
            "task": "openvolunteer.tickets.tasks.cancel_stale_tickets",
            "crontab": midnight,
            "kwargs": json.dumps(
                {
                    "statuses": ["in_progress", "blocked"],
                    "days_stale": 10,
                    "new_status": "canceled",
                },
            ),
            "enabled": True,
            "description": "Cancel old tasks that have not been modified in 30 days",
        },
    )

    cancel_tix_canceled_events = PeriodicTask.objects.get_or_create(
        name="Cancel tickets for canceled events",
        defaults={
            "task": "openvolunteer.tickets.tasks.cancel_tickets_for_canceled_events",
            "crontab": midnight,
            "kwargs": json.dumps(
                {
                    "days_recent": 1,
                    "new_status": "canceled",
                },
            ),
            "enabled": True,
            "description": (
                "Cancel tickets that are associated with "
                "canceled events. There is a default buffer to prevent "
                "issues with accidental deletions of events"
            ),
        },
    )

    delete_completed_tickets = PeriodicTask.objects.get_or_create(
        name="Delete completed tickets after 30 days",
        defaults={
            "task": "openvolunteer.tickets.tasks.delete_tickets",
            "crontab": midnight,
            "kwargs": json.dumps(
                {
                    "days_old": 30,
                    "statuses": ["completed", "canceled"],
                },
            ),
            "enabled": True,
        },
    )

    delete_ticket_batches = PeriodicTask.objects.get_or_create(
        name="Delete any dangling ticket batches",
        defaults={
            "task": "openvolunteer.tickets.tasks.delete_ticket_batches",
            "crontab": midnight,
            "enabled": True,
        },
    )

    return {
        "delete_completed_tickets": delete_completed_tickets,
        "create_intro_tix": create_intro_tix,
        "cancel_stale_tix": cancel_stale_tix,
        "cancel_tix_canceled_events": cancel_tix_canceled_events,
        "delete_ticket_batches": delete_ticket_batches,
    }

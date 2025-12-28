from openvolunteer.events.models import EventTemplate
from openvolunteer.events.models import ShiftAssignmentStatus

from .actions.models import TicketActionButtonColor
from .actions.models import TicketActionTemplate
from .actions.models import TicketActionType
from .models import TicketStatus
from .models import TicketTemplate


def install_default_ticket_actions():
    """
    Install global TicketActionTemplates.
    """

    create_assignment, _ = TicketActionTemplate.objects.get_or_create(
        slug="create_assignment",
        action_type=TicketActionType.CREATE_SHIFT_ASSIGNMENT,
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
        action_type=TicketActionType.CREATE_SHIFT_ASSIGNMENT,
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
        "create_assignment": create_assignment,
        "create_assignment_partial": create_assignment_partial,
        "complete_ticket": complete_ticket,
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
                "We're happy you are here and wanted to know if you were "
                "interested in volunteering?\n"
                "\n"
                "Please let us know!\n"
                "```\n"
                "\n"
                "4. Await their response\n"
                "\n"
                "5. If they confirm their interest, click the `confirm` action button. "
                "If they are not interested, click the `reject` action button."
            ),
            "default_priority": 1,
            "claimable": True,
        },
    )
    if created:
        introduction.action_templates.set(
            [actions["complete_ticket"], actions["close_ticket"]],
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
                "{{event_type}} on {{starts_at_date}}"
                "at {{starts_at_time.cdt}}?\n"
                "\n"
                "Please let us know!\n"
                "```\n"
                "\n"
                "4. Await their response\n"
                "\n"
                "5. If they confirm their interest, click the `confirm` action button. "
                "If they are not interested, click the `reject` action button.\n"
            ),
            "default_priority": 1,
            "claimable": True,
        },
    )
    if created:
        recruit.action_templates.set(
            [
                actions["create_assignment"],
                actions["create_assignment_partial"],
                actions["close_ticket"],
            ],
        )

    reconfirmation, created = TicketTemplate.objects.get_or_create(
        name="Reconfirmation",
        defaults={
            "ticket_name_template": "Reconfirm {{person.discord}} for {{event.title}}",
            "description_template": (
                "Hi {{person.discord}}!\n"
                "Please reconfirm your availability for "
                "**{{ event.title }}** on {{ starts_at_date }}.\n"
                "See You soon!"
            ),
            "default_priority": 2,
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
                "**{{ event.title }}**."
                "Contact {{event.owned_by}} for more details."
            ),
            "default_priority": 3,
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

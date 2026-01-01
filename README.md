# Open Volunteer

Volunteer organizational software

License: BSD

## What is this?

Open Volunteer allows organizations to track and assign volunteers to activities and manage the lifecycle of these same volunteers.

For example, here's a view of a phone banking event managed in the UI. Notice how you can track the status of assignees (Confirmed, declined, etc). You also have tickets which can be assigned to particular events:

![View of a phonebanking event](./docs/event-view.png)

Tickets will help users to complete important outreach tasks and track outreach to volunteers:

![View of a introduction ticket](./docs/ticket-view.png)

The idea is that we can assign tickets to users, who will work through these tickets to accomplish auditable and real goals:

![View of a home page](./docs/home-view.png)

## Basic Commands

All local development requires `docker` to run locally.

### Setting up local stack

To start the local dev environment, first run:

```
docker compose -f docker-compose.local.yml up
```

This brings up all the containers required for local development:

1. Django
2. Postgres
3. Celery
4. Redis
5. Node
6. etc etc

### Setting Up Your Users

- To create a **normal user account**, just go to Sign Up and fill out the form. Once you submit it, you'll see a "Verify Your E-mail Address" page. Go to your console to see a simulated email verification message. Copy the link into your browser. Now the user's email should be verified and ready to go.

```
$ docker logs openvolunteer_local_django
...
To: libdough@destiny.gg
Date: Wed, 31 Dec 2025 04:50:52 -0000
Message-ID: <176715665223.25.4790457677486040098@3ed59bd90a5c>

Hello from Open Volunteer!

You're receiving this email because user libdough has given your email address to register an account on example.com.

To confirm this is correct, go to http://localhost:3000/accounts/confirm-email/Mg:1vaoAe:aqYqcasuNQti1rFVLkKfMwpJRCFX12Joepn-HiZPRjU/
```

Copying this link into the browser will create the user

- To create a **superuser account**, use this command:

```
docker compose -f docker-compose.local.yml run --rm django python manage.py createsuperuser
```

For convenience, you can keep your normal user logged in on Chrome and your superuser logged in on Firefox (or similar), so that you can see how the site behaves for both kinds of users.

### DB Migrations

Any change to a models.py file will require creating new DB migrations

```
docker compose -f docker-compose.local.yml run --rm django python manage.py makemigrations
```

The above will create the relevant migration files for all modules in this repository. To actually run the migrations, use the following:

```
docker compose -f docker-compose.local.yml run --rm django python manage.py migrate
```

Assuming that

### Reset local dev

If you need to, it might be useful to reset the local dev environment:

```
docker compose -f docker-compose.local.yml down -v
```

This will drop all volumes and reset everything. This allows you to start completely from scratch

### Run unit tests

> TODO: Implement docs for unit tests

<!-- ### Type checks

Running type checks with mypy:

    uv run mypy openvolunteer

### Test coverage

To run the tests, check your test coverage, and generate an HTML coverage report:

    uv run coverage run -m pytest
    uv run coverage html
    uv run open htmlcov/index.html

#### Running tests with pytest

    uv run pytest

### Live reloading and Sass CSS compilation

Moved to [Live reloading and SASS compilation](https://cookiecutter-django.readthedocs.io/en/latest/2-local-development/developing-locally.html#using-webpack-or-gulp).

 -->

## Navigating this repo

There are several concepts you should understand when you try making changes/understanding how this code base works.

### Modules

There are a few important modules that are defined inside [/openvolunter/](openvolunteer/) directory.

1. [people](openvolunteer/people/)
   - Handles all the people and contacts that we are managing
2. [events](openvolunteer/events/)
   - Handles events and activities that we create (Canvassing, phone banking, etc etc)
3. [orgs](openvolunteer/orgs/)
   - Tenant based system for grouping people, events, etc into specific actionable organizations. Users will be granted roles to control what actions and permissions they have within the group
4. [tickets](openvolunteer/tickets/)
   - For each org, we will create tickets (i.e. tasks) that users can claim to accomplish specific goals.
   - For example, we might create tickets to recruit contacts to participate in up coming event. Or, we can create tickets to track progress on securing specific venues. Etc etc.
   - This module also includes `Actions` which are automations associated with tickets to make managing contacts easier.
5. [users](openvolunteer/users/)
   - Authenticated accounts which have access to openvolunteer
   - Distinct from contacts, these users have elevated positions in your organization and are responsible for all outreach and decision making.

There is also [templates in openvolunteer/](openvolunteer/templates/) which currently has all the frontend elements used in the UI.

### Common Files

There are a few common files you should be aware of. In no particular order:

1. models.py
   - Holds all the DB files that the module uses.
2. migrations/
   - Directory which contains all the needed DB migrations a module requires (i.e. creating new tables/columns/etc)
3. apps.py
   - Defines the module as is imported by Django to reference a modules features
4. admin.py
   - Defines all the admin UI in the `http://localhost:3000/admin` pages
   - Very useful for maintance and debugging
5. views.py
   - Controls all the UI renderings, API forms, etc
   - The way most business logic will be exposed to users
6. filters.py
   - For some views, there will be filters exposed in the UI (e.g. filter by event)
   - These define a programtic set of filters that are rendered in the UI and utilized in the backend to accomplish filterings
7. permissions.py
   - All permissions are defined as helper functions in these folders
   - Typically, permissions will take the user and the relevant org. Retrieving the user's role in the org is the main method by which Authz is determined.
8. forms.py
   - All API forms are defined in these files. These tell Django about the request schemas used for modifying/retrieving data in the DB.
9. tasks.py
   - Django utilizes [Celery](https://docs.celeryq.dev/en/main/getting-started/introduction.html) as a task queue
   - These files define the tasks exposed to Celery to run periodically
   - Actually scheduling tasks requires utilizing the Admin pages
10. services.py
    - Some modules requires specialized services (i.e. running actions like updating a person's tags)

There are a few other files I've utilized in this repo (i.e. queryset.py or tests.py), but the above are the main ones you will find interesting and relevant.

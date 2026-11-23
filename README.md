# GameMatch

A web platform for finding people to play with. Players create a profile, pick the games they play, send invitations, and talk in real time once an invitation is accepted. Players can also rate each other, so reliable teammates are easy to spot.

Built as an engineering thesis project (Vistula University, Computer Science).

## What it does

- Registration with consent to data processing, login, account deletion
- Profile with avatar, bio, language and a list of games with region and mode
- Player search per game, filtered by region, mode, language and minimum trust
- Invitations: send, accept, decline
- Real-time chat between players whose invitation was accepted
- Trust rating (1 to 3 stars with a comment), shown on the profile once a player has at least three ratings

## Stack

Python, Flask, SQLAlchemy, PostgreSQL, Flask-SocketIO, Flask-Migrate, Flask-Bcrypt, Flask-WTF.

## Running locally

You need Python 3.10+ and a PostgreSQL server.

Create an empty database:

    CREATE DATABASE gamematch;

Install dependencies:

    python -m venv venv
    venv\Scripts\activate
    pip install -r requirements.txt

On Linux or macOS activate with `source venv/bin/activate` instead.

Create a `.env` file in the project root:

    SECRET_KEY=any-long-random-string
    DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/gamematch

Create the tables and start the app:

    flask --app main db upgrade
    python main.py

The site runs at http://localhost:5000.

## Project layout

    app/
      models/      database models
      routes/      pages and JSON endpoints, one blueprint per area
      sockets/     Socket.IO events for chat and online status
      templates/   Jinja2 templates
      static/      CSS, JavaScript, images
      utils/       decorators and helpers
    migrations/    Alembic migrations
    tests/         automated tests (pytest)
    main.py        entry point

## Tests

Install the development dependencies and run the suite (SQLite in memory by default):

    pip install -r requirements-dev.txt
    pytest

To run the same tests on PostgreSQL, point `TEST_DATABASE_URL` at an empty test database.
The database is wiped before every test, so never use a production database:

    $env:TEST_DATABASE_URL = "postgresql+psycopg://user:password@localhost:5432/gm_test"
    pytest

`tests/perf_measure.py` seeds 1000 accounts and prints median and p95 response times.

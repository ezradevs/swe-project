#!/bin/bash
# This script adds seed data to the SQLite database for testing purposes.

echo "Adding seed members to the database..."
sqlite3 data/main.db < data/seed_members.sql
echo "Adding seed tournaments to the database..."
sqlite3 data/main.db < data/seed_tournaments.sql
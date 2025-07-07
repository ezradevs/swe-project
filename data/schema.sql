-- This SQL script creates the necessary tables for the tournament management system. It includes tables for users, tournaments, matches, and scores.

-- Admins table (for login)
DROP TABLE IF EXISTS users;

CREATE TABLE
    users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        is_admin INTEGER DEFAULT 1
    );

-- Members table (no login)
DROP TABLE IF EXISTS members;

CREATE TABLE
    members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT,
        rating INTEGER DEFAULT 1200,
        joined_at TEXT DEFAULT (datetime ('now'))
    );

DROP TABLE IF EXISTS tournaments;

CREATE TABLE
    tournaments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        date TEXT NOT NULL,
        location TEXT NOT NULL,
        format TEXT NOT NULL
    );

-- Tournament Participants table
DROP TABLE IF EXISTS tournament_participants;

CREATE TABLE
    IF NOT EXISTS tournament_participants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tournament_id INTEGER,
        member_id INTEGER,
        FOREIGN KEY (tournament_id) REFERENCES tournaments (id),
        FOREIGN KEY (member_id) REFERENCES members (id)
    );

-- Fixtures table
DROP TABLE IF EXISTS fixtures;

CREATE TABLE
    IF NOT EXISTS fixtures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tournament_id INTEGER,
        round INTEGER,
        player1_id INTEGER,
        player2_id INTEGER,
        result TEXT DEFAULT 'TBD',
        FOREIGN KEY (tournament_id) REFERENCES tournaments (id),
        FOREIGN KEY (player1_id) REFERENCES members (id),
        FOREIGN KEY (player2_id) REFERENCES members (id)
    );
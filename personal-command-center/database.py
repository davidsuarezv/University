import sqlite3
from datetime import datetime

# This function creates a connection to our database
# Think of it like opening a file, but for databases
def get_connection():
    """
    Creates and returns a connection to the SQLite database.
    SQLite is a simple database that stores everything in a single file (data.db).
    """
    conn = sqlite3.connect('data/data.db')
    # This line makes it so we can access columns by name (like a dictionary)
    conn.row_factory = sqlite3.Row
    return conn

# This function sets up all our tables (like creating spreadsheets)
def initialize_database():
    """
    Creates all the tables we need if they don't exist yet.
    Tables are like spreadsheets - each one stores different data.
    """
    conn = get_connection()
    cursor = conn.cursor()  # cursor lets us execute SQL commands
    
    # Create assignments table
    # This stores all your school assignments
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            course TEXT,
            due_date TEXT,
            completed INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # What each column means:
    # - id: unique number for each assignment (auto-generated)
    # - title: what the assignment is called
    # - course: which class it's for
    # - due_date: when it's due
    # - completed: 0 = not done, 1 = done
    # - created_at: when you added it
    
    # Create habits table
    # This tracks your daily habits (gym, duolingo, bible, etc.)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            streak INTEGER DEFAULT 0,
            last_completed TEXT
        )
    ''')
    # What each column means:
    # - name: habit name (e.g., "Gym", "Duolingo")
    # - streak: how many days in a row you've done it
    # - last_completed: the last date you checked it off
    
    # Create habit_logs table
    # This keeps a record of every day you complete a habit
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS habit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_id INTEGER,
            completed_date TEXT,
            FOREIGN KEY (habit_id) REFERENCES habits(id)
        )
    ''')
    # This links to the habits table so we can see your history
    
    # Create workouts table
    # This stores each workout session
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            exercise_type TEXT,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # - exercise_type: e.g., "Chest & Triceps", "Legs", "Cardio"
    # - notes: anything you want to remember about that workout
    
    conn.commit()  # Save all changes to the database
    conn.close()   # Close the connection

# Run this when the file is executed directly
if __name__ == "__main__":
    import os
    # Create the data folder if it doesn't exist
    os.makedirs('data', exist_ok=True)
    initialize_database()
    print("✅ Database initialized successfully!")
import sqlite3
import os

class DBManager:
    def __init__(self, db_name="youtube_factory.db"):
        os.makedirs("data", exist_ok=True)
        self.db_path = os.path.join("data", db_name)
        self.conn = sqlite3.connect(self.db_path)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_name TEXT UNIQUE, niche TEXT, visual_style TEXT,
                language TEXT, pov TEXT, structure TEXT, parts TEXT,
                target_minutes TEXT, char_style TEXT, bg_style TEXT,
                scene_style TEXT, dna_content TEXT, style_content TEXT, topic_content TEXT
            )
        ''')
        self.conn.commit()

    def get_all_profiles(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT channel_name FROM profiles")
        return [row[0] for row in cursor.fetchall()]
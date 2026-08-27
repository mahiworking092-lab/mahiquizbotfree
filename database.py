import aiosqlite
import json
import random
import string
from config import DATABASE_PATH

def generate_quiz_id(length=8):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

async def init_db():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS quizzes (
            quiz_id TEXT PRIMARY KEY,
            creator_id INTEGER,
            creator_name TEXT,
            title TEXT,
            description TEXT,
            timer INTEGER DEFAULT 20,
            shuffle INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            question_id INTEGER PRIMARY KEY AUTOINCREMENT,
            quiz_id TEXT,
            section_name TEXT DEFAULT 'General',
            question_text TEXT,
            options_json TEXT,
            correct_option INTEGER,
            explanation TEXT,
            photo_file_id TEXT,
            FOREIGN KEY (quiz_id) REFERENCES quizzes(quiz_id) ON DELETE CASCADE
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS quiz_sessions (
            session_id TEXT PRIMARY KEY,
            quiz_id TEXT,
            chat_id INTEGER,
            status TEXT DEFAULT 'running',
            current_q_index INTEGER DEFAULT 0,
            timer_sec INTEGER,
            is_paused INTEGER DEFAULT 0,
            started_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS user_answers (
            session_id TEXT,
            question_id INTEGER,
            user_id INTEGER,
            user_name TEXT,
            is_correct INTEGER,
            time_taken REAL,
            PRIMARY KEY (session_id, question_id, user_id)
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS schedules (
            schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
            quiz_id TEXT,
            chat_id INTEGER,
            creator_id INTEGER,
            time_str TEXT,
            is_active INTEGER DEFAULT 1
        )
        """)
        await db.commit()

async def save_user(user_id: int, username: str, full_name: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
        INSERT INTO users (user_id, username, full_name)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET username=?, full_name=?
        """, (user_id, username, full_name, username, full_name))
        await db.commit()

async def create_quiz(creator_id: int, creator_name: str, title: str, description: str = "", timer: int = 20, shuffle: int = 1) -> str:
    quiz_id = generate_quiz_id()
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
        INSERT INTO quizzes (quiz_id, creator_id, creator_name, title, description, timer, shuffle)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (quiz_id, creator_id, creator_name, title, description, timer, shuffle))
        await db.commit()
    return quiz_id

async def add_question(quiz_id: str, question_text: str, options: list, correct_option: int, section_name: str = "General", explanation: str = "", photo_file_id: str = None):
    options_json = json.dumps(options, ensure_ascii=False)
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
        INSERT INTO questions (quiz_id, section_name, question_text, options_json, correct_option, explanation, photo_file_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (quiz_id, section_name, question_text, options_json, correct_option, explanation, photo_file_id))
        await db.commit()

async def get_quiz(quiz_id: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM quizzes WHERE quiz_id = ?", (quiz_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def get_quiz_questions(quiz_id: str, shuffle: bool = False):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM questions WHERE quiz_id = ? ORDER BY question_id ASC", (quiz_id,)) as cursor:
            rows = await cursor.fetchall()
            questions = [dict(r) for r in rows]
            for q in questions:
                q['options'] = json.loads(q['options_json'])
            if shuffle:
                random.shuffle(questions)
            return questions

async def get_user_quizzes(user_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM quizzes WHERE creator_id = ? ORDER BY created_at DESC", (user_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def delete_quiz(quiz_id: str, user_id: int) -> bool:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("DELETE FROM quizzes WHERE quiz_id = ? AND creator_id = ?", (quiz_id, user_id))
        await db.commit()
        return cursor.rowcount > 0

async def record_answer(session_id: str, question_id: int, user_id: int, user_name: str, is_correct: int, time_taken: float = 0.0):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
        INSERT INTO user_answers (session_id, question_id, user_id, user_name, is_correct, time_taken)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(session_id, question_id, user_id) DO UPDATE SET is_correct=?, time_taken=?
        """, (session_id, question_id, user_id, user_name, is_correct, time_taken, is_correct, time_taken))
        await db.commit()

async def get_session_leaderboard(session_id: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
        SELECT 
            user_id,
            user_name,
            SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) as correct_count,
            SUM(CASE WHEN is_correct = 0 THEN 1 ELSE 0 END) as wrong_count,
            COUNT(*) as total_answered
        FROM user_answers
        WHERE session_id = ?
        GROUP BY user_id, user_name
        ORDER BY correct_count DESC, wrong_count ASC
        """, (session_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def add_schedule(quiz_id: str, chat_id: int, creator_id: int, time_str: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
        INSERT INTO schedules (quiz_id, chat_id, creator_id, time_str)
        VALUES (?, ?, ?, ?)
        """, (quiz_id, chat_id, creator_id, time_str))
        await db.commit()

async def get_user_schedules(creator_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM schedules WHERE creator_id = ? AND is_active = 1", (creator_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def remove_schedule(schedule_id: int, creator_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("UPDATE schedules SET is_active = 0 WHERE schedule_id = ? AND creator_id = ?", (schedule_id, creator_id))
        await db.commit()

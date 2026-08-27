import asyncio
import json
import time
import random
import string

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import ContextTypes
from database import (
    get_quiz, get_quiz_questions, record_answer, get_session_leaderboard
)
from image_generator import generate_leaderboard_image

# In-memory active sessions: { chat_id: session_data }
active_sessions = {}


def _gen_session_id():
    return "S" + "".join(random.choices(string.ascii_uppercase + string.digits, k=10))


async def start_quiz_session(update: Update, context: ContextTypes.DEFAULT_TYPE, quiz_id: str):
    """Starts a quiz in the current chat (private or group)."""
    chat = update.effective_chat
    user = update.effective_user

    if chat.id in active_sessions:
        msg = update.message or (update.callback_query and update.callback_query.message)
        if msg:
            await msg.reply_text("⚠️ Is chat me ek quiz pehle se chal rahi hai! Pehle `/stop` karein.")
        return

    quiz = await get_quiz(quiz_id)
    if not quiz:
        msg = update.message or (update.callback_query and update.callback_query.message)
        if msg:
            await msg.reply_text("❌ Quiz not found.")
        return

    questions = await get_quiz_questions(quiz_id, shuffle=bool(quiz.get("shuffle", 1)))
    if not questions:
        msg = update.message or (update.callback_query and update.callback_query.message)
        if msg:
            await msg.reply_text("❌ Is quiz me koi question nahi hai.")
        return

    session_id = _gen_session_id()
    session = {
        "session_id": session_id,
        "quiz_id": quiz_id,
        "quiz": quiz,
        "questions": questions,
        "chat_id": chat.id,
        "current_index": 0,
        "timer": quiz.get("timer", 20),
        "is_paused": False,
        "is_stopped": False,
        "started_by": user.id,
        "poll_to_question": {},   # poll_id -> question_id
        "poll_correct": {},       # poll_id -> correct_option_id
        "poll_send_time": {},     # poll_id -> timestamp
        "current_section": None,
    }
    active_sessions[chat.id] = session

    # Send quiz start banner
    msg = update.message or (update.callback_query and update.callback_query.message)
    banner = (
        f"🚀 <b>Quiz Starting!</b>\n\n"
        f"📝 <b>{quiz['title']}</b>\n"
        f"❓ Questions: {len(questions)}\n"
        f"⏰ Timer: {session['timer']}s per question\n\n"
        f"<i>Get ready...</i>"
    )
    await msg.reply_text(banner, parse_mode="HTML")
    await asyncio.sleep(2)

    # Start sending questions
    await _send_next_question(context, chat.id)


async def _send_next_question(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """Sends the next question as a Telegram Quiz Poll."""
    session = active_sessions.get(chat_id)
    if not session or session["is_stopped"]:
        return

    idx = session["current_index"]
    questions = session["questions"]

    if idx >= len(questions):
        # Quiz finished
        await _finish_quiz(context, chat_id)
        return

    q = questions[idx]

    # Section transition banner
    section = q.get("section_name", "General")
    if section != session.get("current_section"):
        session["current_section"] = section
        section_banner = f"📚 <b>Section: {section}</b> (Q{idx + 1} onwards)"
        await context.bot.send_message(chat_id=chat_id, text=section_banner, parse_mode="HTML")
        await asyncio.sleep(1)

    # Send photo if present
    if q.get("photo_file_id"):
        try:
            await context.bot.send_photo(chat_id=chat_id, photo=q["photo_file_id"])
        except Exception:
            pass

    # Send Quiz Poll
    options = q["options"]
    correct_idx = q["correct_option"]
    explanation = q.get("explanation", "")

    try:
        poll_msg = await context.bot.send_poll(
            chat_id=chat_id,
            question=f"Q{idx + 1}. {q['question_text']}",
            options=options,
            type="quiz",
            correct_option_id=correct_idx,
            explanation=explanation[:200] if explanation else None,
            open_period=session["timer"],
            is_anonymous=False,
        )

        poll_id = poll_msg.poll.id
        session["poll_to_question"][poll_id] = q["question_id"]
        session["poll_correct"][poll_id] = correct_idx
        session["poll_send_time"][poll_id] = time.time()

    except Exception as e:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"⚠️ Error sending Q{idx + 1}: {e}"
        )

    session["current_index"] = idx + 1

    # Schedule next question after timer + 2s buffer
    await asyncio.sleep(session["timer"] + 2)

    # Check if paused
    while session.get("is_paused") and not session.get("is_stopped"):
        await asyncio.sleep(1)

    if not session.get("is_stopped"):
        await _send_next_question(context, chat_id)


async def handle_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles user poll answers and records them."""
    poll_answer = update.poll_answer
    user = poll_answer.user
    poll_id = poll_answer.poll_id
    selected_options = poll_answer.option_ids

    # Find which session this poll belongs to
    for chat_id, session in active_sessions.items():
        if poll_id in session["poll_to_question"]:
            question_id = session["poll_to_question"][poll_id]
            correct_idx = session["poll_correct"][poll_id]
            send_time = session["poll_send_time"].get(poll_id, time.time())
            time_taken = round(time.time() - send_time, 2)

            is_correct = 1 if (selected_options and selected_options[0] == correct_idx) else 0

            await record_answer(
                session_id=session["session_id"],
                question_id=question_id,
                user_id=user.id,
                user_name=user.full_name or user.first_name or "User",
                is_correct=is_correct,
                time_taken=time_taken,
            )
            break


async def _finish_quiz(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """Finishes the quiz and sends the leaderboard image."""
    session = active_sessions.pop(chat_id, None)
    if not session:
        return

    session_id = session["session_id"]
    quiz = session["quiz"]
    total_qs = len(session["questions"])

    leaderboard = await get_session_leaderboard(session_id)

    if not leaderboard:
        await context.bot.send_message(
            chat_id=chat_id,
            text="🏁 <b>Quiz Finished!</b>\n\nKisi ne bhi answer nahi diya 😢",
            parse_mode="HTML",
        )
        return

    # Generate graphical leaderboard image
    try:
        img_buf = generate_leaderboard_image(quiz["title"], leaderboard, total_qs)
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=InputFile(img_buf, filename="leaderboard.png"),
            caption=f"🏆 <b>{quiz['title']} — Final Leaderboard!</b>\nTotal Questions: {total_qs}",
            parse_mode="HTML",
        )
    except Exception as e:
        # Fallback: text leaderboard
        text = f"🏆 <b>{quiz['title']} — Leaderboard</b>\n\n"
        medals = {0: "🥇", 1: "🥈", 2: "🥉"}
        for i, entry in enumerate(leaderboard[:10]):
            medal = medals.get(i, f"#{i+1}")
            name = entry["user_name"]
            correct = entry["correct_count"]
            wrong = entry["wrong_count"]
            pct = int(correct / total_qs * 100) if total_qs else 0
            text += f"{medal} {name} — ✅ {correct} | ❌ {wrong} | {pct}%\n"
        await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")


async def quiz_command_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /quiz <quiz_id> in group chat."""
    if not context.args:
        await update.message.reply_text("Usage: `/quiz <quiz_id>`", parse_mode="Markdown")
        return
    quiz_id = context.args[0]
    await start_quiz_session(update, context, quiz_id)

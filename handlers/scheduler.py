from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import add_schedule, get_user_schedules, remove_schedule, get_quiz
from handlers.quiz_runner import start_quiz_session


async def schedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Schedule a quiz: /schedule <quiz_id> <HH:MM>"""
    user = update.effective_user
    chat = update.effective_chat

    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: `/schedule <quiz_id> <HH:MM>`\n"
            "Example: `/schedule ABC12345 14:30`",
            parse_mode="Markdown",
        )
        return

    quiz_id = context.args[0]
    time_str = context.args[1]

    # Validate time format
    try:
        parts = time_str.split(":")
        hour, minute = int(parts[0]), int(parts[1])
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Invalid time format. Use HH:MM (24h). Example: `14:30`", parse_mode="Markdown")
        return

    quiz = await get_quiz(quiz_id)
    if not quiz:
        await update.message.reply_text("❌ Quiz not found.")
        return

    await add_schedule(quiz_id, chat.id, user.id, time_str)

    # Register APScheduler job
    job_name = f"sched_{quiz_id}_{chat.id}_{time_str}"
    context.job_queue.run_daily(
        _scheduled_quiz_callback,
        time=__import__("datetime").time(hour=hour, minute=minute),
        chat_id=chat.id,
        name=job_name,
        data={"quiz_id": quiz_id, "chat_id": chat.id},
    )

    await update.message.reply_text(
        f"✅ <b>Quiz Scheduled!</b>\n\n"
        f"📝 Quiz: <b>{quiz['title']}</b>\n"
        f"⏰ Daily at: <b>{time_str}</b>\n"
        f"💬 Chat: This chat\n\n"
        f"Use `/schedules` to view, `/unschedule <id>` to cancel.",
        parse_mode="HTML",
    )


async def _scheduled_quiz_callback(context: ContextTypes.DEFAULT_TYPE):
    """Callback for APScheduler to auto-run a quiz."""
    job = context.job
    data = job.data
    quiz_id = data["quiz_id"]
    chat_id = data["chat_id"]

    quiz = await get_quiz(quiz_id)
    if not quiz:
        await context.bot.send_message(chat_id=chat_id, text="❌ Scheduled quiz not found, skipping.")
        return

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"⏰ <b>Scheduled Quiz Auto-Starting!</b>\n📝 {quiz['title']}",
        parse_mode="HTML",
    )

    # Create a pseudo update for start_quiz_session
    from handlers.quiz_runner import active_sessions, _gen_session_id, _send_next_question, get_quiz_questions
    import asyncio

    if chat_id in active_sessions:
        await context.bot.send_message(chat_id=chat_id, text="⚠️ Quiz already running in this chat.")
        return

    questions = await get_quiz_questions(quiz_id, shuffle=bool(quiz.get("shuffle", 1)))
    if not questions:
        await context.bot.send_message(chat_id=chat_id, text="❌ No questions in this quiz.")
        return

    session_id = _gen_session_id()
    session = {
        "session_id": session_id,
        "quiz_id": quiz_id,
        "quiz": quiz,
        "questions": questions,
        "chat_id": chat_id,
        "current_index": 0,
        "timer": quiz.get("timer", 20),
        "is_paused": False,
        "is_stopped": False,
        "started_by": 0,
        "poll_to_question": {},
        "poll_correct": {},
        "poll_send_time": {},
        "current_section": None,
    }
    active_sessions[chat_id] = session

    await _send_next_question(context, chat_id)


async def schedules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View active schedules. Also handles btn_schedules callback."""
    user = update.effective_user
    query = update.callback_query
    if query:
        await query.answer()

    schedules = await get_user_schedules(user.id)

    if not schedules:
        text = "⏰ <b>My Schedules</b>\n\nKoi active schedule nahi hai."
        keyboard = [[InlineKeyboardButton("🔙 Main Menu", callback_data="btn_main_menu")]]
        if query:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        else:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return

    text = "⏰ <b>Active Schedules:</b>\n\n"
    for s in schedules:
        text += f"• ID: <code>{s['schedule_id']}</code> | Quiz: <code>{s['quiz_id']}</code> | Time: <b>{s['time_str']}</b>\n"

    text += "\n`/unschedule <id>` to remove."
    keyboard = [[InlineKeyboardButton("🔙 Main Menu", callback_data="btn_main_menu")]]

    if query:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


async def unschedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove a schedule: /unschedule <schedule_id>"""
    user = update.effective_user

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: `/unschedule <schedule_id>`", parse_mode="Markdown")
        return

    schedule_id = int(context.args[0])
    await remove_schedule(schedule_id, user.id)

    # Try to remove APScheduler job
    jobs = context.job_queue.get_jobs_by_name(f"sched_")
    for j in context.job_queue.jobs():
        if str(schedule_id) in (j.name or ""):
            j.schedule_removal()

    await update.message.reply_text(f"✅ Schedule #{schedule_id} removed!", parse_mode="HTML")

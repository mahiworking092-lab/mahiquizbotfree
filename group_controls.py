from telegram import Update
from telegram.ext import ContextTypes
from handlers.quiz_runner import active_sessions


async def pause_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pause the running quiz in this chat."""
    chat_id = update.effective_chat.id
    session = active_sessions.get(chat_id)

    if not session:
        await update.message.reply_text("⚠️ Is chat me koi quiz nahi chal rahi.")
        return

    if session["is_paused"]:
        await update.message.reply_text("⏸ Quiz pehle se paused hai. `/resume` use karein.")
        return

    session["is_paused"] = True
    await update.message.reply_text("⏸ <b>Quiz Paused!</b>\n`/resume` se continue karein.", parse_mode="HTML")


async def resume_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Resume a paused quiz."""
    chat_id = update.effective_chat.id
    session = active_sessions.get(chat_id)

    if not session:
        await update.message.reply_text("⚠️ Is chat me koi quiz nahi chal rahi.")
        return

    if not session["is_paused"]:
        await update.message.reply_text("▶️ Quiz already running!")
        return

    session["is_paused"] = False
    await update.message.reply_text("▶️ <b>Quiz Resumed!</b> Next question aa raha hai...", parse_mode="HTML")


async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop the running quiz and show results."""
    chat_id = update.effective_chat.id
    session = active_sessions.get(chat_id)

    if not session:
        await update.message.reply_text("⚠️ Is chat me koi quiz nahi chal rahi.")
        return

    session["is_stopped"] = True
    session["is_paused"] = False

    answered = session["current_index"]
    total = len(session["questions"])
    await update.message.reply_text(
        f"🛑 <b>Quiz Stopped!</b>\n"
        f"Questions Answered: {answered}/{total}\n"
        f"Generating Leaderboard...",
        parse_mode="HTML",
    )

    # Trigger leaderboard finish
    from handlers.quiz_runner import _finish_quiz
    await _finish_quiz(context, chat_id)


async def fast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reduce the timer mid-quiz. Usage: /fast 10"""
    chat_id = update.effective_chat.id
    session = active_sessions.get(chat_id)

    if not session:
        await update.message.reply_text("⚠️ Is chat me koi quiz nahi chal rahi.")
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: `/fast 10` (seconds)", parse_mode="Markdown")
        return

    new_timer = max(5, int(context.args[0]))
    session["timer"] = new_timer
    await update.message.reply_text(f"⚡ <b>Timer reduced to {new_timer}s per question!</b>", parse_mode="HTML")


async def slow_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Increase the timer mid-quiz. Usage: /slow 30"""
    chat_id = update.effective_chat.id
    session = active_sessions.get(chat_id)

    if not session:
        await update.message.reply_text("⚠️ Is chat me koi quiz nahi chal rahi.")
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: `/slow 30` (seconds)", parse_mode="Markdown")
        return

    new_timer = min(300, int(context.args[0]))
    session["timer"] = new_timer
    await update.message.reply_text(f"🐢 <b>Timer increased to {new_timer}s per question!</b>", parse_mode="HTML")

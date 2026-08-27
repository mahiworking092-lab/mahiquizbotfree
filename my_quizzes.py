from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import get_user_quizzes, delete_quiz, get_quiz_questions, get_quiz
import json


async def my_quizzes_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's created quizzes list."""
    user = update.effective_user
    query = update.callback_query

    if query:
        await query.answer()

    quizzes = await get_user_quizzes(user.id)

    if not quizzes:
        text = "📚 <b>My Quizzes</b>\n\nAapne abhi tak koi quiz nahi banayi."
        keyboard = [[InlineKeyboardButton("➕ Create New Quiz", callback_data="btn_create_quiz")]]
        if query:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        else:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return

    text = "📚 <b>My Quizzes:</b>\n\n"
    keyboard = []
    for q in quizzes[:20]:
        text += f"• <b>{q['title']}</b> | ID: <code>{q['quiz_id']}</code> | ⏰ {q['timer']}s\n"
        keyboard.append([
            InlineKeyboardButton(f"📋 {q['title'][:20]}", callback_data=f"viewquiz_{q['quiz_id']}"),
        ])

    keyboard.append([InlineKeyboardButton("➕ Create New Quiz", callback_data="btn_create_quiz")])
    keyboard.append([InlineKeyboardButton("🔙 Main Menu", callback_data="btn_main_menu")])

    if query:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


async def view_quiz_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show single quiz details with action buttons."""
    query = update.callback_query
    await query.answer()
    quiz_id = query.data.replace("viewquiz_", "")

    quiz = await get_quiz(quiz_id)
    if not quiz:
        await query.edit_message_text("❌ Quiz not found or deleted.")
        return

    questions = await get_quiz_questions(quiz_id)
    bot_username = context.bot.username

    start_url = f"https://t.me/{bot_username}?start=quiz_{quiz_id}"
    group_url = f"https://t.me/{bot_username}?startgroup=quiz_{quiz_id}"

    import urllib.parse
    share_text = (
        "Quiz Created! 💬\n\n"
        f"💳 Name: {quiz['title']}\n"
        f"#️⃣ Questions: {len(questions)}\n"
        f"⏰ Timer: {quiz['timer']}s\n"
        f"🆔 ID: {quiz_id}\n"
        f"💰 Type: free\n"
        f"💀 -ve: 0.00\n"
        f"👧 Creator: {quiz['creator_name']}\n\n"
        f"👇 Click link below to play Quiz:"
    )
    direct_share_url = f"https://t.me/share/url?url={urllib.parse.quote(start_url)}&text={urllib.parse.quote(share_text)}"

    text = (
        "Quiz Created! 💬\n\n"
        f"💳 <b>Name:</b> {quiz['title']}\n"
        f"#️⃣ <b>Questions:</b> {len(questions)}\n"
        f"⏰ <b>Timer:</b> {quiz['timer']}s\n"
        f"🆔 <b>ID:</b> <code>{quiz_id}</code>\n"
        f"💰 <b>Type:</b> free\n"
        f"💀 <b>-ve:</b> 0.00\n"
        f"👧 <b>Creator:</b> {quiz['creator_name']}"
    )

    keyboard = [
        [InlineKeyboardButton("🎯 Start", url=start_url), InlineKeyboardButton("🚀 Group", url=group_url)],
        [InlineKeyboardButton("🔗 Share", url=direct_share_url), InlineKeyboardButton("📤 Inline Share", switch_inline_query=quiz_id)],
        [InlineKeyboardButton("📥 Export JSON", callback_data=f"export_{quiz_id}"), InlineKeyboardButton("🗑 Delete Quiz", callback_data=f"delquiz_{quiz_id}")],
        [InlineKeyboardButton("🔙 My Quizzes", callback_data="btn_my_quizzes")],
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


async def export_quiz_json(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Export quiz questions as JSON file."""
    query = update.callback_query
    await query.answer("Exporting...")
    quiz_id = query.data.replace("export_", "")

    quiz = await get_quiz(quiz_id)
    questions = await get_quiz_questions(quiz_id)

    if not quiz or not questions:
        await query.edit_message_text("❌ Quiz not found.")
        return

    export_data = {
        "quiz_id": quiz_id,
        "title": quiz["title"],
        "timer": quiz["timer"],
        "questions": [
            {
                "question": q["question_text"],
                "options": q["options"],
                "correct_option": q["correct_option"],
                "section": q.get("section_name", "General"),
                "explanation": q.get("explanation", ""),
            }
            for q in questions
        ],
    }
    json_str = json.dumps(export_data, ensure_ascii=False, indent=2)
    import io
    file_buf = io.BytesIO(json_str.encode("utf-8"))
    file_buf.name = f"quiz_{quiz_id}.json"

    await context.bot.send_document(
        chat_id=update.effective_chat.id,
        document=file_buf,
        filename=f"quiz_{quiz_id}.json",
        caption=f"📥 Exported: <b>{quiz['title']}</b>",
        parse_mode="HTML",
    )


async def delete_quiz_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm and delete a quiz."""
    query = update.callback_query
    await query.answer()
    quiz_id = query.data.replace("delquiz_", "")

    keyboard = [
        [InlineKeyboardButton("✅ Yes, Delete", callback_data=f"confirmdelete_{quiz_id}"),
         InlineKeyboardButton("❌ Cancel", callback_data="btn_my_quizzes")],
    ]
    await query.edit_message_text(
        f"⚠️ <b>Are you sure you want to delete Quiz <code>{quiz_id}</code>?</b>\nThis action cannot be undone!",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )


async def confirm_delete_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Actually delete the quiz."""
    query = update.callback_query
    await query.answer()
    quiz_id = query.data.replace("confirmdelete_", "")
    user = update.effective_user

    success = await delete_quiz(quiz_id, user.id)
    if success:
        await query.edit_message_text(f"✅ Quiz <code>{quiz_id}</code> deleted successfully!", parse_mode="HTML")
    else:
        await query.edit_message_text("❌ Could not delete. Maybe not your quiz?")

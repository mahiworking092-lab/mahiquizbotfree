from telegram import Update, InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import get_quiz, get_quiz_questions

async def inline_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query_text = update.inline_query.query.strip()
    if not query_text:
        return

    quiz_id = query_text
    quiz = await get_quiz(quiz_id)
    if not quiz:
        return

    questions = await get_quiz_questions(quiz_id)
    bot_username = context.bot.username

    start_url = f"https://t.me/{bot_username}?start=quiz_{quiz_id}"
    group_url = f"https://t.me/{bot_username}?startgroup=quiz_{quiz_id}"

    card_text = (
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
        [InlineKeyboardButton("🎯 Start", url=start_url)],
        [InlineKeyboardButton("🚀 Group", url=group_url)],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    results = [
        InlineQueryResultArticle(
            id=quiz_id,
            title=f"💳 {quiz['title']}",
            description=f"Questions: {len(questions)} | Timer: {quiz['timer']}s | ID: {quiz_id}",
            input_message_content=InputTextMessageContent(
                message_text=card_text,
                parse_mode="HTML"
            ),
            reply_markup=reply_markup
        )
    ]

    await update.inline_query.answer(results, cache_time=5)

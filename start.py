from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import save_user, get_quiz
import handlers.quiz_runner as quiz_runner

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    await save_user(user.id, user.username or "", user.full_name)

    # Check deep link arguments (e.g. /start quiz_ABC123XY)
    if context.args:
        arg = context.args[0]
        if arg.startswith("quiz_"):
            quiz_id = arg.replace("quiz_", "")
            quiz = await get_quiz(quiz_id)
            if quiz:
                await quiz_runner.start_quiz_session(update, context, quiz_id)
                return
            else:
                await update.message.reply_text("❌ Quiz not found or has been deleted.")
                return

    # If in Group Chat
    if chat.type in ['group', 'supergroup']:
        keyboard = [
            [InlineKeyboardButton("➕ Create Quiz in Bot DM", url=f"https://t.me/{context.bot.username}?start=create")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"👋 Hello {user.mention_html()}!\n\n"
            "🤖 I am your **Multi-User Quiz Bot**!\n"
            "Use `/quiz <quiz_id>` or share a Quiz Card to launch a Quiz in this group!\n\n"
            "💡 Commands available in group:\n"
            "• `/pause` & `/resume`\n"
            "• `/stop` - Stop quiz & generate Leaderboard\n"
            "• `/fast 10` or `/slow 30` - Change timer",
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        return

    # In Private Chat
    keyboard = [
        [InlineKeyboardButton("➕ Create New Quiz", callback_data="btn_create_quiz")],
        [InlineKeyboardButton("📚 My Quizzes", callback_data="btn_my_quizzes"), InlineKeyboardButton("⏰ My Schedules", callback_data="btn_schedules")],
        [InlineKeyboardButton("📤 Share Quiz", switch_inline_query=""), InlineKeyboardButton("❓ Help & Commands", callback_data="btn_help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_text = (
        f"🌟 <b>Welcome to Ultra Quiz Bot, {user.mention_html()}!</b> 🌟\n\n"
        "✨ <b>Features:</b>\n"
        "• Bilkul FREE Multi-user Quiz Creation\n"
        "• 500+ Questions Bulk `.txt` & Poll Forwarding\n"
        "• Photo/Image Questions Support\n"
        "• Dynamic Timers, Sectional Quizzes & Live Group Controls\n"
        "• 🥇 🏆 Graphic Image Leaderboard Card\n"
        "• 1-Click Inline Sharing Card!\n\n"
        "Bataiye aap aaj kya karna chahte hain?"
    )

    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="HTML")
    elif update.callback_query:
        await update.callback_query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode="HTML")

async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    help_text = (
        "📖 <b>Bot Help & Commands:</b>\n\n"
        "<b>Private Chat Commands:</b>\n"
        "• `/createquiz` - Interactive Quiz Creator\n"
        "• `/myquizzes` - View, Edit, Share, or Delete your quizzes\n"
        "• `/schedules` - View active quiz schedules\n"
        "• `/schedule <quiz_id> <HH:MM>` - Schedule a quiz\n\n"
        "<b>Group Commands:</b>\n"
        "• `/pause` & `/resume` - Pause or resume running quiz\n"
        "• `/stop` - Stop running quiz & generate leaderboard image\n"
        "• `/fast <seconds>` - Reduce question timer\n"
        "• `/slow <seconds>` - Increase question timer\n\n"
        "<b>Bulk Upload Format:</b>\n"
        "File upload karne par `.txt` me har question transform hoga:\n"
        "<code>Q: Question text?\nA) Opt 1\nB) Opt 2 ✅\nC) Opt 3\n---</code>"
    )
    keyboard = [[InlineKeyboardButton("🔙 Main Menu", callback_data="btn_main_menu")]]
    await query.edit_message_text(help_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters
)
from database import create_quiz, add_question, get_quiz, get_quiz_questions
from txt_parser import parse_txt_questions

(TITLE, DESCRIPTION, TIMER, ADD_QUESTIONS) = range(4)

async def create_quiz_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        await query.message.reply_text("✏️ Please enter the **Title** of your Quiz:")
    else:
        await update.message.reply_text("✏️ Please enter the **Title** of your Quiz:")
    return TITLE

async def quiz_title_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    title = update.message.text.strip()
    context.user_data['create_title'] = title

    keyboard = [
        [InlineKeyboardButton("⏩ Skip Description", callback_data="skip_desc")]
    ]
    await update.message.reply_text(
        f"✅ Title saved: <b>{title}</b>\n\nNow enter a short <b>Description</b> for this quiz (or click Skip):",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    return DESCRIPTION

async def quiz_desc_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        desc = update.message.text.strip()
    else:
        query = update.callback_query
        await query.answer()
        desc = ""
    context.user_data['create_desc'] = desc

    keyboard = [
        [InlineKeyboardButton("10 sec", callback_data="timer_10"), InlineKeyboardButton("15 sec", callback_data="timer_15")],
        [InlineKeyboardButton("20 sec", callback_data="timer_20"), InlineKeyboardButton("30 sec", callback_data="timer_30")],
        [InlineKeyboardButton("60 sec", callback_data="timer_60")]
    ]
    text = "⏱️ Select the per-question <b>Timer</b>:"
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    return TIMER

async def quiz_timer_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    timer_sec = int(query.data.replace("timer_", ""))
    context.user_data['create_timer'] = timer_sec

    # Create Quiz record in SQLite database
    user = update.effective_user
    quiz_id = await create_quiz(
        creator_id=user.id,
        creator_name=user.full_name,
        title=context.user_data['create_title'],
        description=context.user_data['create_desc'],
        timer=timer_sec
    )
    context.user_data['active_quiz_id'] = quiz_id

    keyboard = [
        [InlineKeyboardButton("📥 Done & Finish Quiz", callback_data="finish_quiz_create")]
    ]

    msg_text = (
        f"🎉 <b>Quiz Created! ID: <code>{quiz_id}</code></b>\n\n"
        "Ab aap questions add kar sakte hain:\n"
        "1. <b>Text Format:</b> Send question text with options and mark correct option with ✅\n"
        "2. <b>Bulk .txt File:</b> Upload a `.txt` file containing questions!\n"
        "3. <b>Poll Forwarding:</b> Dusre channel se Telegram Poll forward karein.\n"
        "4. <b>Photo Question:</b> Send a Photo with caption/question!\n\n"
        "Jab saare questions add ho jaayein, click <b>Done & Finish</b> below."
    )
    await query.edit_message_text(msg_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    return ADD_QUESTIONS

async def question_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    quiz_id = context.user_data.get('active_quiz_id')
    if not quiz_id:
        await update.message.reply_text("❌ No active quiz found. Please type `/createquiz` to start.")
        return ConversationHandler.END

    # 1. Check if Document (.txt file)
    if update.message.document:
        doc = update.message.document
        if doc.file_name and (doc.file_name.lower().endswith('.txt') or doc.file_name.lower().endswith('.json')):
            file_obj = await doc.get_file()
            byte_content = await file_obj.download_as_bytearray()
            txt_content = byte_content.decode('utf-8-sig', errors='ignore')

            parsed_qs = parse_txt_questions(txt_content)
            if not parsed_qs:
                await update.message.reply_text("⚠️ No valid questions could be parsed from the .txt file. Please check format.")
                return ADD_QUESTIONS

            for q in parsed_qs:
                await add_question(
                    quiz_id=quiz_id,
                    question_text=q['question_text'],
                    options=q['options'],
                    correct_option=q['correct_option'],
                    section_name=q.get('section_name', 'General'),
                    explanation=q.get('explanation', '')
                )
            
            await update.message.reply_text(f"✅ Successfully added <b>{len(parsed_qs)}</b> questions from file!", parse_mode="HTML")
            return ADD_QUESTIONS

    # 2. Check if Native Poll (Forwarded poll)
    if update.message.poll:
        poll = update.message.poll
        options = [opt.text for opt in poll.options]
        correct_idx = poll.correct_option_id if poll.correct_option_id is not None else 0
        await add_question(
            quiz_id=quiz_id,
            question_text=poll.question,
            options=options,
            correct_option=correct_idx,
            explanation=poll.explanation or ""
        )
        await update.message.reply_text(f"✅ Forwarded Poll added as Question!", parse_mode="HTML")
        return ADD_QUESTIONS

    # 3. Check if Photo Question
    if update.message.photo:
        photo = update.message.photo[-1]
        caption = update.message.caption or "Question Image"
        
        # Try to parse options from caption
        lines = [line.strip() for line in caption.split('\n') if line.strip()]
        q_text = lines[0] if lines else "Look at the image and answer:"
        options = []
        correct_idx = 0
        for idx, l in enumerate(lines[1:]):
            if "✅" in l:
                correct_idx = len(options)
                l = l.replace("✅", "").strip()
            options.append(l)

        if len(options) < 2:
            options = ["Option A", "Option B", "Option C", "Option D"]

        await add_question(
            quiz_id=quiz_id,
            question_text=q_text,
            options=options,
            correct_option=correct_idx,
            photo_file_id=photo.file_id
        )
        await update.message.reply_text("✅ Image Question added successfully!", parse_mode="HTML")
        return ADD_QUESTIONS

    # 4. Direct Text Input
    text = update.message.text
    if text:
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        q_text = lines[0]
        options = []
        correct_idx = 0
        for line in lines[1:]:
            if "✅" in line or "[c]" in line.lower():
                correct_idx = len(options)
                line = line.replace("✅", "").replace("[c]", "").strip()
            options.append(line)

        if len(options) < 2:
            await update.message.reply_text(
                "⚠️ Please provide at least 2 options for the question.\nExample:\n"
                "Capital of France?\nParis ✅\nLondon\nBerlin"
            )
            return ADD_QUESTIONS

        await add_question(
            quiz_id=quiz_id,
            question_text=q_text,
            options=options,
            correct_option=correct_idx
        )
        await update.message.reply_text("✅ Question added successfully! Send another or click Done below.", parse_mode="HTML")
        return ADD_QUESTIONS

    return ADD_QUESTIONS

async def finish_quiz_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    quiz_id = context.user_data.get('active_quiz_id')

    quiz = await get_quiz(quiz_id)
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

    keyboard = [
        [InlineKeyboardButton("🎯 Start", url=start_url)],
        [InlineKeyboardButton("🚀 Group", url=group_url)],
        [InlineKeyboardButton("🔗 Share", url=direct_share_url), InlineKeyboardButton("📤 Inline Share", switch_inline_query=quiz_id)]
    ]

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

    await query.edit_message_text(card_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    return ConversationHandler.END

async def cancel_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Quiz creation cancelled.")
    return ConversationHandler.END

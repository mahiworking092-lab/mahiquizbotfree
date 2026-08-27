import os
import sys
import logging

# Ensure root directory of project is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ConversationHandler, MessageHandler, PollAnswerHandler,
    InlineQueryHandler, filters,
)
from config import BOT_TOKEN
from database import init_db

from handlers.start import start_command, help_callback
from handlers.create import (
    create_quiz_start, quiz_title_received, quiz_desc_received,
    quiz_timer_received, question_input_handler, finish_quiz_creation,
    cancel_creation, TITLE, DESCRIPTION, TIMER, ADD_QUESTIONS,
)
from handlers.quiz_runner import (
    quiz_command_group, handle_poll_answer,
)
from handlers.my_quizzes import (
    my_quizzes_handler, view_quiz_detail, export_quiz_json,
    delete_quiz_handler, confirm_delete_quiz,
)
from handlers.group_controls import (
    pause_command, resume_command, stop_command, fast_command, slow_command,
)
from handlers.scheduler import (
    schedule_command, schedules_command, unschedule_command,
)
from handlers.inline_share import inline_query_handler

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main():
    """Run the bot."""
    app = Application.builder().token(BOT_TOKEN).build()

    # ──────────── Conversation Handler for Quiz Creation ────────────
    create_conv = ConversationHandler(
        entry_points=[
            CommandHandler("createquiz", create_quiz_start),
            CallbackQueryHandler(create_quiz_start, pattern="^btn_create_quiz$"),
        ],
        states={
            TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, quiz_title_received)],
            DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, quiz_desc_received),
                CallbackQueryHandler(quiz_desc_received, pattern="^skip_desc$"),
            ],
            TIMER: [CallbackQueryHandler(quiz_timer_received, pattern=r"^timer_\d+$")],
            ADD_QUESTIONS: [
                MessageHandler(
                    (filters.TEXT & ~filters.COMMAND) | filters.Document.ALL | filters.PHOTO | filters.POLL,
                    question_input_handler,
                ),
                CallbackQueryHandler(finish_quiz_creation, pattern="^finish_quiz_create$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_creation)],
        per_user=True,
        per_chat=True,
    )
    app.add_handler(create_conv)

    # ──────────── Command Handlers ────────────
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("myquizzes", my_quizzes_handler))
    app.add_handler(CommandHandler("quiz", quiz_command_group))
    app.add_handler(CommandHandler("schedule", schedule_command))
    app.add_handler(CommandHandler("schedules", schedules_command))
    app.add_handler(CommandHandler("unschedule", unschedule_command))

    # Group Live Controls
    app.add_handler(CommandHandler("pause", pause_command))
    app.add_handler(CommandHandler("resume", resume_command))
    app.add_handler(CommandHandler("stop", stop_command))
    app.add_handler(CommandHandler("fast", fast_command))
    app.add_handler(CommandHandler("slow", slow_command))

    # ──────────── Callback Query Handlers ────────────
    app.add_handler(CallbackQueryHandler(my_quizzes_handler, pattern="^btn_my_quizzes$"))
    app.add_handler(CallbackQueryHandler(schedules_command, pattern="^btn_schedules$"))
    app.add_handler(CallbackQueryHandler(help_callback, pattern="^btn_help$"))
    app.add_handler(CallbackQueryHandler(start_command, pattern="^btn_main_menu$"))
    app.add_handler(CallbackQueryHandler(view_quiz_detail, pattern=r"^viewquiz_"))
    app.add_handler(CallbackQueryHandler(export_quiz_json, pattern=r"^export_"))
    app.add_handler(CallbackQueryHandler(delete_quiz_handler, pattern=r"^delquiz_"))
    app.add_handler(CallbackQueryHandler(confirm_delete_quiz, pattern=r"^confirmdelete_"))

    # ──────────── Poll Answer Handler ────────────
    app.add_handler(PollAnswerHandler(handle_poll_answer))

    # ──────────── Inline Query Handler ────────────
    app.add_handler(InlineQueryHandler(inline_query_handler))

    # ──────────── Initialize DB & Run ────────────
    import asyncio

    async def post_init(application: Application):
        await init_db()
        logger.info("✅ Database initialized!")

    app.post_init = post_init

    logger.info("🚀 Bot is starting...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

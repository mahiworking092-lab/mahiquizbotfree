# 🤖 Ultra Telegram Quiz Bot

Multi-user, free-for-all Telegram Quiz Bot with graphical leaderboards, inline sharing, live group controls, scheduler, and Railway deployment support.

## ✨ Features

- **Multi-User Quiz Creation** — Anyone can create quizzes via bot DM
- **Multiple Question Formats** — Text, .txt bulk upload, forwarded polls, image questions
- **Live Group Controls** — `/pause`, `/resume`, `/stop`, `/fast`, `/slow`
- **Sectional Quiz** — Subject/section grouping with transition banners
- **Graphic Leaderboard** — Pillow (PIL) rendered PNG image leaderboard card (🥇🥈🥉)
- **Inline Quiz Card Share** — 1-click share full quiz card via Telegram Inline Mode
- **Deep Link Integration** — `🎯 Start in Chat` and `🚀 Run in Group` buttons
- **Quiz Scheduler** — Auto-start quizzes at scheduled times
- **Railway Ready** — Dockerfile, Procfile, nixpacks.toml included

---

## 🚀 Railway Deployment (Free Hosting)

### Step 1: Create GitHub Repository

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/telegram-quiz-bot.git
git push -u origin main
```

### Step 2: Deploy on Railway

1. Go to [railway.app](https://railway.app) and sign in with GitHub
2. Click **"New Project"** → **"Deploy from GitHub Repo"**
3. Select your `telegram-quiz-bot` repository
4. Railway will auto-detect the `Dockerfile` and start building

### Step 3: Set Environment Variables

In Railway Dashboard → Your Project → **Variables** tab, add:

| Variable | Value |
|----------|-------|
| `BOT_TOKEN` | Your token from [@BotFather](https://t.me/BotFather) |
| `BOT_USERNAME` | Your bot username (without @) |
| `DATABASE_PATH` | `quiz_bot.db` |
| `ADMIN_IDS` | Your Telegram User ID (comma separated) |

### Step 4: Enable Inline Mode

1. Open [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/setinline` → Select your bot → Set placeholder text like `Enter Quiz ID to share`
3. This enables the 📤 Share Quiz Card feature

### Step 5: Verify

Send `/start` to your bot on Telegram. You should see the welcome menu!

---

## 📁 Project Structure

```
telegram_quiz_bot/
├── bot.py                  # Main entry point
├── config.py               # Environment & settings
├── database.py             # SQLite async storage
├── image_generator.py      # Pillow leaderboard renderer
├── txt_parser.py           # Bulk .txt question parser
├── handlers/
│   ├── __init__.py
│   ├── start.py            # /start & deep links
│   ├── create.py           # Quiz creation wizard
│   ├── quiz_runner.py      # Live quiz engine
│   ├── inline_share.py     # Inline mode sharing
│   ├── my_quizzes.py       # /myquizzes manager
│   ├── scheduler.py        # /schedule engine
│   └── group_controls.py   # /pause /resume /stop /fast /slow
├── Procfile
├── Dockerfile
├── nixpacks.toml
├── requirements.txt
├── .env.example
└── README.md
```

---

## 📝 Bulk Question .txt Format

```
Q: What is the capital of India?
A) Mumbai
B) New Delhi ✅
C) Kolkata
D) Chennai
Exp: New Delhi is the capital of India since 1931.
---
Q: Who discovered gravity?
A) Einstein
B) Newton ✅
C) Tesla
D) Edison
---
```

You can also use section headers:
```
[Section: History]
Q: When did India gain independence?
A) 1945
B) 1947 ✅
C) 1950
D) 1942
---
```

---

## 🤖 Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Main menu |
| `/createquiz` | Start quiz creation wizard |
| `/myquizzes` | View/edit/delete your quizzes |
| `/quiz <id>` | Run a quiz in group |
| `/pause` | Pause running quiz |
| `/resume` | Resume paused quiz |
| `/stop` | Stop quiz & show leaderboard |
| `/fast <sec>` | Reduce timer mid-quiz |
| `/slow <sec>` | Increase timer mid-quiz |
| `/schedule <id> <HH:MM>` | Schedule auto quiz |
| `/schedules` | View active schedules |
| `/unschedule <id>` | Remove a schedule |
| `/cancel` | Cancel quiz creation |

---

## License

MIT License — Free to use, modify, and distribute.

#!/bin/bash
# Prepares yad2_monitor for push to GitHub (run with computer off).
# Run from inside yad2_monitor directory.

set -e
cd "$(dirname "$0")"

echo "=== Yad2 Monitor – הכנה לדחיפה ל-GitHub ==="
echo ""

if [ ! -f main.py ] || [ ! -d .github ]; then
  echo "Error: Run this script from the yad2_monitor directory."
  exit 1
fi

# Ensure we have a repo
if [ ! -d .git ]; then
  git init
  git branch -M main
  echo "Initialized git repo."
fi

# Add only what we need (no .venv, .env)
git add .github/
git add config.py main.py notifier.py report_page.py scraper.py local_db.py
git add requirements.txt env.example run.sh README.md DEPLOY.md .gitignore
# Add report so Pages has something on first deploy (workflow will overwrite)
if [ -f report.html ]; then git add report.html; fi

git status
if git diff --cached --quiet 2>/dev/null && [ -z "$(git status --porcelain)" ]; then
  echo "Nothing to commit. Repo may already be up to date."
else
  git commit -m "Yad2 monitor – 24/7 via Actions" || true
fi

echo ""
echo "--- עכשיו בצע את הצעדים הבאים ---"
echo "1. צור ריפו ריק ב-GitHub: https://github.com/new (שם למשל: yad2-monitor)"
echo "2. הרץ (החלף YOUR_USER ו-YOUR_REPO):"
echo ""
echo "   git remote add origin https://github.com/YOUR_USER/YOUR_REPO.git"
echo "   git push -u origin main"
echo ""
echo "3. ב-GitHub: Settings → Secrets → הוסף TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID"
echo "4. Actions → Yad2 Monitor → Run workflow"
echo "5. Settings → Pages → Source: main, / (root) → Save"
echo ""
echo "הדוח מהנייד: https://YOUR_USER.github.io/YOUR_REPO/report.html"
echo ""

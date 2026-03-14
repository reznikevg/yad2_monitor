# הפעלה עם מחשב כבוי (GitHub Actions + Pages)

כדי שהניטור ירוץ 24/7 והדוח יהיה נגיש מהנייד **בלי להשאיר את המחשב דלוק**, בצע את הצעדים הבאים.

---

## 1. צור ריפו חדר ב-GitHub

1. היכנס ל-[github.com](https://github.com) ולחץ **New repository**.
2. **Repository name:** למשל `yad2-monitor` (או כל שם).
3. **Public**, אל תסמן "Add README" (ריפו ריק).
4. **Create repository**.

---

## 2. דחוף את הקוד מהמחשב

**מהטרמינל** (בתיקיית הפרויקט):

```bash
cd /Users/evgeniyre/MyFirstControl/yad2_monitor

# אם עדיין אין git
git init
git branch -M main

# הוסף קבצים (ללא .venv ו-.env)
git add .github config.py main.py notifier.py report_page.py scraper.py local_db.py requirements.txt env.example run.sh README.md .gitignore
git add report.html

# קומיט ראשון
git commit -m "Yad2 monitor – 24/7 via Actions"

# חבר לריפו שיצרת (החלף USER ו-REPO בשם המשתמש ושם הריפו)
git remote add origin https://github.com/USER/REPO.git

# דחיפה
git push -u origin main
```

**החלף** `USER` ב־שם המשתמש ב-GitHub ו־`REPO` ב־שם הריפו (למשל `yad2-monitor`).

---

## 3. הגדר Secrets (טלגרם / ווטסאפ)

1. בריפו: **Settings** → **Secrets and variables** → **Actions**.
2. **New repository secret** לכל אחד:
   - `TELEGRAM_BOT_TOKEN` – הטוקן מבוטFather.
   - `TELEGRAM_CHAT_ID` – ה־Chat ID.
   - (אופציונלי) `WHATSAPP_WEBHOOK_URL` – כתובת ה-Webhook.

---

## 4. הפעל ריצה ראשונה

1. **Actions** → **Yad2 Monitor** → **Run workflow** → **Run workflow**.
2. חכה לסיום (כ־2–4 דקות). אחרי הריצה יופיעו קומיטים עם `report.html` ו־`local_db.json`.

---

## 5. הפעל GitHub Pages (גישה מהנייד)

1. **Settings** → **Pages**.
2. **Source:** Deploy from a branch.
3. **Branch:** `main` → **/ (root)** → **Save**.
4. אחרי דקה־שתיים הדוח יהיה זמין בכתובת:

```
https://USER.github.io/REPO/report.html
```

(החלף USER ו-REPO כמו קודם.)

**גישה מהנייד:** פתח את הכתובת הזו בדפדפן – מכל רשת, גם עם מחשב כבוי.

---

## סיכום

| פעולה              | איפה / איך |
|--------------------|------------|
| סריקה אוטומטית    | כל 10 דקות, 24/7 (GitHub Actions). |
| צפייה בדוח         | `https://USER.github.io/REPO/report.html` מהנייד או מהמחשב. |
| עדכונים מידיים    | טלגרם (ו־ווטסאפ אם הוגדר) לפי ה-Secrets. |

אחרי שהגדרת את כל השלבים – **אפשר לכבות את המחשב**; הניטור והדוח ימשיכו לעבוד מענן GitHub.

# דחיפה ל-GitHub – הרץ אצלך בטרמינל

ה-remote כבר מחובר. נשאר רק לדחוף (פעם אחת):

```bash
cd /Users/evgeniyre/MyFirstControl/yad2_monitor
git push -u origin main
```

אם יבקשו התחברות – התחבר ל-GitHub (או השתמש ב־token אם מוגדר).

---

## אחרי שה-push הצליח – ב-GitHub:

### 1. Secrets (טלגרם)
- **Settings** → **Secrets and variables** → **Actions** → **New repository secret**
- הוסף: `TELEGRAM_BOT_TOKEN` , `TELEGRAM_CHAT_ID` (ו־`WHATSAPP_WEBHOOK_URL` אם צריך)

### 2. הרצה ראשונה
- **Actions** → **Yad2 Monitor** → **Run workflow** → **Run workflow**
- חכה 2–4 דקות. יופיעו קומיטים עם report.html

### 3. GitHub Pages (גישה מהנייד)
- **Settings** → **Pages**
- **Source:** Deploy from a branch
- **Branch:** main → **/ (root)** → **Save**

### 4. הכתובת מהנייד
```
https://reznikevg.github.io/yad2_monitor/report.html
```

זהו – אחרי זה הכל רץ 24/7 עם מחשב כבוי.

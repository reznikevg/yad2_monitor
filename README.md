# Yad2 Real Estate Rent Monitor

ניטור מודעות נדל״ן להשכרה מיד2: שני חיפושים, בדיקה כל 10 דקות, דיווח יומי מלא, ודף מקומי לצפייה בתוצאות.

## Setup

```bash
cd yad2_monitor
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install chromium
```

אם `playwright install` נכשל (פרוקסי/תעודות), הרץ אותו בסביבה עם אינטרנט רגיל.

## הרצה

**חשוב:** להריץ מתוך תיקיית `yad2_monitor` ולהשתמש ב־venv (או `python3`):

```bash
cd /Users/evgeniyre/MyFirstControl/yad2_monitor
.venv/bin/python main.py --test
.venv/bin/python main.py --send-now
```

או (אם הסקריפט ללא CRLF):

```bash
cd /Users/evgeniyre/MyFirstControl/yad2_monitor
./run.sh --test
./run.sh --send-now
```

**ריצה חד־פעמית** (גריפה של שני החיפושים, עדכון DB ו־report.html):

```bash
.venv/bin/python main.py
```

**מצב Scheduler** – בדיקה כל 10 דקות + דיווח יומי פעם ביום:

```bash
.venv/bin/python main.py --schedule
```

**שליחת בדיקה** (הודעה קצרה לכל הערוצים המוגדרים):

```bash
.venv/bin/python main.py --test
```

אופציות:

- `--url <URL>` – חיפוש בודד (מצב legacy).
- `--db <path>` – נתיב ל־`local_db.json`.
- `--report <path>` – נתיב ל־`report.html`.
- `--no-headless` – להציג חלון דפדפן.
- `--schedule` – להפעיל לולאה: כל 10 דקות בדיקה, פעם ב־24 שעות דיווח מלא.
- `--serve` – להפעיל שרת HTTP כדי לצפות בדוח מהטלפון (אותה רשת WiFi).
- `--serve-port <port>` – פורט ל־`--serve` (ברירת מחדל 8765).
- `--skip-if-inactive` – יציאה ללא ריצה אם מחוץ ל־6:00–24:00 (לשימוש ב־CI).

**אם מופיע Captcha (ShieldSquare – "Are you for real?")** הרץ עם דפדפן גלוי; הסקריפט יזהה ויחכה עד שתפתור:
`.venv/bin/python main.py --no-headless` — סמן "אני לא רובוט", Submit, והמתן.

## חיפושים (config.py)

1. **גוש דן (חולון)** – עד 15,000 ₪, 3+ חדרים, חניה, ממ״ד.  
   `tel-aviv-area?maxPrice=15000&minRooms=3&...&neighborhood=793`
2. **מרכז והשרון** – עד 10,000 ₪, 4+ חדרים, חניה, ממ״ד.  
   `center-and-sharon?maxPrice=10000&minRooms=4&...&multiNeighborhood=470,991420,991421`

## התנהגות

- **כל 10 דקות (בין 06:00 ל־24:00):** גריפה של שני ה־URLs, השוואה ל־`local_db.json`. אם נכנסה **מודעה חדשה** או **שונה מחיר** — נשלח **עדכון מידי** לקונסול ולטלגרם (ולשירות ווטסאפ אם הוגדר). גם אם אין כל הפרטים (טלפון וכו') — העדכון נשלח עם מה שיש.
- **מחוץ לחלון (00:00–06:00):** המחזור מדולג (לא מריצים גריפה).
- **פעם ביום:** דיווח מלא של כל המודעות (דיווח יומי).
- **דף מקומי:** `report.html` מתעדכן בכל מחזור — פתח בדפדפן לצפייה.

## הוספת Telegram

מימוש `BaseNotifier` עם `send_full_report()` ו־`send_changes()`, והעברת המופע ל־`run_cycle(..., notifier=...)` / `run_scheduler(..., notifier=...)`.

## קישור לצפייה בתוצאות

הדף המקומי מתעדכן בכל ריצה. לפתיחה בדפדפן:

- **קובץ:** `yad2_monitor/report.html`  
- **לינק (בדפדפן):** `file:///Users/evgeniyre/MyFirstControl/yad2_monitor/report.html`  

אפשר גם לפתוח את הקובץ בדאבל-קליק.

### גישה מהטלפון (אותה רשת WiFi)

כדי לפתוח את הדוח בדפדפן בטלפון:

1. **במחשב** (בטרמינל, מתוך `yad2_monitor`):
   ```bash
   .venv/bin/python main.py --serve
   ```
2. יופיעו שני כתובות, למשל:
   - `http://127.0.0.1:8765/report.html` — מהמחשב
   - `http://192.168.1.105:8765/report.html` — מהטלפון
3. **בטלפון** — וודא שהטלפון מחובר **לאותה רשת WiFi** כמו המחשב, ופתח בדפדפן את הכתובת עם ה־IP (השורה השנייה).
4. השאר את הטרמינל פתוח; לעצירה: Ctrl+C.

אם צריך פורט אחר: ` .venv/bin/python main.py --serve --serve-port 9000`

## שליחה עכשיו ל-Telegram ו-WhatsApp

הרצה:

```bash
export TELEGRAM_BOT_TOKEN="..."
export TELEGRAM_CHAT_ID="..."
export WHATSAPP_WEBHOOK_URL="https://..."   # אופציונלי
python main.py --send-now
```

זה שולח את **כל** המודעות ששמורות ב־DB (כמו דיווח יומי) לקונסול, לטלגרם (אם הוגדר) ולווטסאפ (אם הוגדר Webhook). אם עדיין לא רצה גריפה, יישלח "אין עדיין מודעות".

- **Telegram:** צור בוט ב־@BotFather, העתק Token. לקבלת Chat ID: שלח הודעה לבוט ואז פתח `https://api.telegram.org/bot<TOKEN>/getUpdates` וחפש `chat.id`.
- **WhatsApp:** צריך שירות שמקבל POST עם JSON (שדה `text`) ומעביר להודעת ווטסאפ (למשל Make.com, n8n, או gateway מותאם). הגדר את ה-URL ב־`WHATSAPP_WEBHOOK_URL`.

ראה `env.example` לדוגמה.

## ריצה עם מחשב כבוי (24/7 מהענן)

**מדריך מלא:** [DEPLOY.md](DEPLOY.md) – צעד־אחר־צעד להעלאה ל-GitHub, הגדרת Secrets ו-Pages, ופתיחת הדוח מהנייד.

**בקצרה:** הרץ `./deploy-to-github.sh` מתוך התיקייה, דחוף לריפו חדר, הגדר Secrets, הפעל Actions ו-Pages. אחרי זה אפשר לכבות את המחשב; הדוח זמין ב־`https://USER.github.io/REPO/report.html`.

---

## ריצה בענן (חינם) – GitHub Actions

אפשר להריץ את הניטור בענן **בלי להשאיר את המחשב דלוק**: GitHub Actions מריץ סריקה כל 10 דקות (ב־6:00–24:00 שעון ישראל), מעדכן את `report.html` ו־`local_db.json` ומדחוף ל־repo. טלגרם/ווטסאפ ממשיכים לעבוד לפי ה־Secrets.

### מה לעשות

1. **להעלות את הפרויקט ל-GitHub**  
   אם הפרויקט בתוך `MyFirstControl`, העלה את כל `MyFirstControl` (כולל `.github/workflows/yad2-monitor.yml` ו־`yad2_monitor`). אם יש לך רק את `yad2_monitor` כ־repo נפרד, העלה אותו ו**ב־`.github/workflows/yad2-monitor.yml`** שנה את `working-directory` ל־`.` (או העתק את ה־workflow לתוך ה־repo של `yad2_monitor` והגדר `working-directory: .`).

2. **להגדיר Secrets**  
   ב־GitHub: Repo → **Settings → Secrets and variables → Actions** → **New repository secret**  
   - `TELEGRAM_BOT_TOKEN` – הטוקן מבוטFather  
   - `TELEGRAM_CHAT_ID` – ה־Chat ID  
   - `WHATSAPP_WEBHOOK_URL` (אופציונלי) – כתובת ה־Webhook לווטסאפ  

3. **להריץ פעם אחת ידנית**  
   **Actions** → **Yad2 Monitor** → **Run workflow** → Run. אחרי הריצה יופיעו קומיטים של `report.html` ו־`local_db.json`.

4. **לצפות בדוח מהטלפון/מכל מקום**  
   - **אפשרות א:** GitHub Pages (חינם ל־repo ציבורי): **Settings → Pages** → Source: **Deploy from a branch** → Branch: `main`, Folder: **/ (root)**. אחרי הדיפלוי הדוח יהיה בכתובת:  
     `https://<USERNAME>.github.io/<REPO>/yad2_monitor/report.html`  
     (אם ה־repo הוא רק `yad2_monitor` אז: `https://<USERNAME>.github.io/<REPO>/report.html`.)  
   - **אפשרות ב:** פשוט לפתוח ב־GitHub את הקובץ `yad2_monitor/report.html` (או `report.html` אם ה־repo הוא רק המוניטור) ולבחור **View raw** או להשתמש ב־**github.dev** ולפתוח את הדוח שם.

### הערות

- **תדירות:** הסריקה רצה כל 10 דקות, 24/7.
- **דקות חינם:** ב־GitHub חשבון חינם יש דקות חודשיות ל־Actions; ריצה כל 10 דקות במשך חודש נשארת בדרך כלל במסגרת החינם.
- **Captcha:** אם יד2 מציג Captcha, ב־CI אי אפשר לפתור ידנית. אם זה קורה הרבה, אפשר להפחית תדירות או להריץ גם מקומית עם `--no-headless` מדי פעם.

## Config

ב־`config.py`: עריכת סלקטורים אם יד2 משנה DOM, הוספת User-Agent, שינוי `CHECK_INTERVAL_MINUTES` / `FULL_REPORT_INTERVAL_HOURS`.

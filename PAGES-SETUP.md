# תיקון 404 – הפעלת GitHub Pages

אם אתה רואה "There isn't a GitHub Pages site here":

## 1. הגדר את מקור האתר

1. ב-repo: **Settings** → **Pages** (בתפריט משמאל).
2. תחת **Build and deployment**:
   - **Source:** בחר **GitHub Actions** (workflow מפרסם את האתר).
3. **Save** (אין צורך לבחור branch או folder).

## 2. הפעל פריסה (פעם אחת)

- **Actions** → **Deploy to Pages** → **Run workflow** → **Run workflow**.
- או פשוט בצע **push** ל־main (גם זה מפעיל את הפריסה).

## 3. המתן דקה–שתיים

אחרי שה-workflow מסתיים, רענן את הכתובת:

- **https://reznikevg.github.io/yad2_monitor/**
- או **https://reznikevg.github.io/yad2_monitor/report.html**

## 4. אם עדיין 404

- וודא שהיה **push** ל־`main` (כולל הקובץ `report.html`).
- ב-**Actions** וודא שאין שגיאות ב-workflow "Yad2 Monitor".
- נסה דפדפן אחר או חלון פרטי (אינקוגניטו).

## 5. כתובת הדוח מהנייד

אחרי ש-Pages עובד:

**https://reznikevg.github.io/yad2_monitor/report.html**

(או רק **https://reznikevg.github.io/yad2_monitor/** – יופנה אוטומטית לדוח.)

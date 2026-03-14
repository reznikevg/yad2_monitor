# תיקון 404 – הפעלת GitHub Pages

אם אתה רואה "There isn't a GitHub Pages site here":

## 1. וודא ש-Pages מופעל

1. ב-repo: **Settings** → **Pages** (בתפריט משמאל).
2. תחת **Build and deployment**:
   - **Source:** בחר **Deploy from a branch** (לא "GitHub Actions").
   - **Branch:** בחר **main**.
   - **Folder:** בחר **/ (root)**.
3. **Save**.

## 2. המתן דקה–שתיים

אחרי השמירה, GitHub בונה את האתר. רענן את הכתובת:

- **https://reznikevg.github.io/yad2_monitor/**
- או **https://reznikevg.github.io/yad2_monitor/report.html**

## 3. אם עדיין 404

- וודא שהיה **push** ל־`main` (כולל הקובץ `report.html`).
- ב-**Actions** וודא שאין שגיאות ב-workflow "Yad2 Monitor".
- נסה דפדפן אחר או חלון פרטי (אינקוגניטו).

## 4. כתובת הדוח מהנייד

אחרי ש-Pages עובד:

**https://reznikevg.github.io/yad2_monitor/report.html**

(או רק **https://reznikevg.github.io/yad2_monitor/** – יופנה אוטומטית לדוח.)

import express from 'express';
import { YemotRouter } from 'yemot-router2';

// דורש Node.js 18+ (fetch מובנה)

const app = express();
const router = YemotRouter({ printLog: true });

const YEMOT_API_URL = 'https://www.call2all.co.il/ym/api/';

// ==========================================================
// אבטחה: רשימת IP-ים מורשים (שרתי Yemot בלבד). השאירו ריק כדי לדלג.
// ==========================================================
const ALLOWED_IPS = (process.env.ALLOWED_IPS || '').split(',').filter(Boolean);

app.use((req, res, next) => {
  if (ALLOWED_IPS.length && !ALLOWED_IPS.includes(req.ip)) {
    console.warn(`בקשה נחסמה מ-IP לא מורשה: ${req.ip}`);
    return res.status(403).send('id_list_message=t-גישה נדחתה');
  }
  next();
});

function cleanExtPath(value) {
  if (!value) return '';
  return value.trim().replace(/\*/g, '/').replace(/-/g, '/').replace(/^\/+|\/+$/g, '');
}

function sanitizeTokenPart(value) {
  if (!value) return '';
  return value.trim().replace(/[^0-9A-Za-z]/g, '');
}

// הקשה של מספר חופשי (עד 10 ספרות, מסתיים בסולמית)
const digitsOptions = { max_digits: 10, min_digits: 1, sec_wait: 15, typing_playback_mode: 'Digits' };

// הקשה בודדת מתוך תפריט
function menuOptions(allowedDigits) {
  return { max_digits: 1, min_digits: 1, sec_wait: 15, typing_playback_mode: 'Digits', digits_allowed: allowedDigits };
}

router.get('/create-playfile', async (call) => {
  try {
    // ---------- פרטי מערכת ----------
    const systemRaw = await call.read(
      [{ type: 'text', data: 'אנא הקישו את מספר המערכת ובסיום הקישו סולמית' }],
      'tap', digitsOptions
    );
    const system = sanitizeTokenPart(systemRaw);

    const passwordRaw = await call.read(
      [{ type: 'text', data: 'אנא הקישו את סיסמת המערכת ובסיום הקישו סולמית' }],
      'tap', digitsOptions
    );
    const password = sanitizeTokenPart(passwordRaw);

    const extensionRaw = await call.read(
      [{ type: 'text', data: 'אנא הקישו את מספר השלוחה החדשה ובסיום הקישו סולמית' }],
      'tap', digitsOptions
    );
    const cleanExt = cleanExtPath(extensionRaw);

    if (!system || !password || !cleanExt) {
      return call.id_list_message([{ type: 'text', data: 'שגיאה: פרטים חסרים או לא תקינים' }]);
    }

    // ---------- שאלה 1: אורך הקובץ ----------
    const sayLength = await call.read(
      [{ type: 'text', data: 'האם להשמיע את אורך הקובץ? 1 כן תמיד. 2 רק אם ארוך מ 5 דקות. 0 לא.' }],
      'tap', menuOptions([0, 1, 2])
    );

    // ---------- שאלה 2: ביפ ----------
    const playBeep = await call.read(
      [{ type: 'text', data: 'ברירת המחדל שיש ביפ בין קבצים. להסיר את הביפ הקישו 1. להשאיר ברירת מחדל הקישו 0.' }],
      'tap', menuOptions([0, 1])
    );

    // ---------- שאלה 3: סדר השמעה ----------
    const playOrder = await call.read(
      [{ type: 'text', data: 'ברירת המחדל השמעה מהחדש לישן. להחליף למינימום הקישו 1. להשאיר ברירת מחדל הקישו 0.' }],
      'tap', menuOptions([0, 1])
    );

    // ---------- שאלה 4: כמות הודעות ----------
    const sayFilesAmount = await call.read(
      [{ type: 'text', data: 'ברירת המחדל לא להשמיע את כמות ההודעות. להשמיע הקישו 1. להשאיר ברירת מחדל הקישו 0.' }],
      'tap', menuOptions([0, 1])
    );

    // ---------- שאלה 5: מקור קבצים ----------
    const sourceExtension = await call.read(
      [{ type: 'text', data: 'ברירת המחדל להשמיע מהשלוחה עצמה. להשמיע משלוחה אחרת הקישו 1. להשאיר ברירת מחדל הקישו 0.' }],
      'tap', menuOptions([0, 1])
    );

    let sourceLine = '';
    if (sourceExtension === '1') {
      const sourcePathRaw = await call.read(
        [{ type: 'text', data: 'אנא הקישו את מספר השלוחה המקור ובסיום הקישו סולמית' }],
        'tap', digitsOptions
      );
      const cleanSource = cleanExtPath(sourcePathRaw);
      if (cleanSource) sourceLine = `folder_to_play=/${cleanSource}`;
    }

    // ---------- שאלה 6: סיום ----------
    const endAction = await call.read(
      [{ type: 'text', data: 'ברירת המחדל לחזור אחורה בסיום. לעבור לשלוחה אחרת הקישו 1. להשאיר ברירת מחדל הקישו 0.' }],
      'tap', menuOptions([0, 1])
    );

    let endLine = '';
    if (endAction === '1') {
      const endExtRaw = await call.read(
        [{ type: 'text', data: 'אנא הקישו את מספר השלוחה אליה תרצו לעבור בסיום ובסיום הקישו סולמית' }],
        'tap', digitsOptions
      );
      const cleanEnd = cleanExtPath(endExtRaw);
      if (cleanEnd) endLine = `playfile_end_goto=/${cleanEnd}`;
    }

    // ---------- שאלה 7: חזרה למיקום אחרון ----------
    const lastPlayAction = await call.read(
      [{ type: 'text', data: 'ברירת המחדל לא לשמור מיקום. לשמור עם תפריט הקישו 1. אוטומטי הקישו 2. להשאיר ברירת מחדל הקישו 0.' }],
      'tap', menuOptions([0, 1, 2])
    );

    // ---------- בניית ext.ini ----------
    const sayLengthValue =
      sayLength === '1' ? 'say_length=yes' :
      sayLength === '2' ? 'playfile_say_length_if=5' :
      'say_length=no';

    const beepLine = playBeep === '1' ? 'play_beep=no' : '';
    const orderLine = playOrder === '1' ? 'start=min' : '';
    const filesAmountLine = sayFilesAmount === '1' ? 'say_files_amount=yes' : '';

    let lastPlayLines = '';
    if (lastPlayAction === '1') lastPlayLines = 'save_last_play=yes\nlast_play_tfr=yes';
    else if (lastPlayAction === '2') lastPlayLines = 'save_last_play=yes\nlast_play_auto=yes';

    const extIni = [
      'type=playfile',
      'after_play=return',
      sayLengthValue,
      beepLine,
      orderLine,
      filesAmountLine,
      sourceLine,
      endLine,
      lastPlayLines,
    ].filter(Boolean).join('\n');

    const token = `${system}:${password}`;

    // ---------- יצירת השלוחה מול API של ימות ----------
    const updateParams = new URLSearchParams({ token, path: `ivr2:${cleanExt}`, type: 'playfile' });
    const r1 = await fetch(`${YEMOT_API_URL}UpdateExtension?${updateParams}`, { signal: AbortSignal.timeout(15000) });
    const r1text = await r1.text();

    if (!(r1.status === 200 && r1text.includes('"responseStatus":"OK"'))) {
      console.error(`UpdateExtension נכשל: ${r1text}`);
      return call.id_list_message([{ type: 'text', data: 'שגיאה ביצירת השלוחה' }]);
    }

    const uploadParams = new URLSearchParams({ token, what: `ivr2:/${cleanExt}/ext.ini`, contents: extIni });
    const r2 = await fetch(`${YEMOT_API_URL}UploadTextFile`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: uploadParams,
      signal: AbortSignal.timeout(15000),
    });
    const r2text = await r2.text();

    if (r2.status === 200 && r2text.includes('"responseStatus":"OK"')) {
      return call.id_list_message([{ type: 'text', data: `שלוחת ההשמעה ${cleanExt} נוצרה` }]);
    } else {
      console.error(`UploadTextFile נכשל: ${r2text}`);
      return call.id_list_message([{ type: 'text', data: 'השלוחה נוצרה אך התפריט לא נטען' }]);
    }
  } catch (err) {
    // ExitError נזרקת ע"י הספרייה בסיום id_list_message - זו לא שגיאה אמיתית
    if (err?.constructor?.name === 'ExitError') throw err;
    console.error(err);
    return call.id_list_message([{ type: 'text', data: 'שגיאה טכנית' }]);
  }
});

app.use(router.asExpressRouter);
app.listen(process.env.PORT || 5000, '0.0.0.0', () => {
  console.log('IVR server running on port', process.env.PORT || 5000);
});

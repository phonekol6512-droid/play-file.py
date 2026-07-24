import re
import os
import logging
import requests
from flask import Flask, request, make_response

app = Flask(__name__)
YEMOT_API_URL = "https://www.call2all.co.il/ym/api/"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ==========================================================
#  אבטחה: רשימת IP-ים מורשים (למשל שרתי Yemot בלבד).
#  אם ריק - לא נבדק (מומלץ למלא בפרודקשן).
#  אפשר להעביר כמשתנה סביבה: ALLOWED_IPS="1.2.3.4,5.6.7.8"
# ==========================================================
ALLOWED_IPS = set(filter(None, os.environ.get("ALLOWED_IPS", "").split(",")))


def ym_response(content: str):
    res = make_response(content)
    res.headers["Content-Type"] = "text/plain; charset=utf-8"
    return res


def ym_read(var_name: str, prompt: str, max_digits=1):
    return ym_response(f"read={prompt}={var_name},{max_digits},12,1,Digits")


def ym_say_and_go_back(text: str):
    """משמיע הודעה וחוזר לתפריט הקודם (ללא ניתוק) - בדיוק כמו ב-create-menu"""
    return ym_response(f"id_list_message={text}")


def sanitize_token_part(value: str) -> str:
    """
    מסיר תווים שעלולים לשבש את בניית ה-token (system:password)
    או לאפשר הזרקת פרמטרים נוספים ל-API של Yemot.
    """
    if value is None:
        return ""
    return re.sub(r"[^0-9A-Za-z]", "", value.strip())


def clean_extension_path(value: str) -> str:
    """מנקה נתיב שלוחה (מחליף * ו- ל-/ ומסיר / מיותרים בקצוות)"""
    if not value:
        return ""
    return value.strip().replace('*', '/').replace('-', '/').strip('/')


@app.before_request
def restrict_ip():
    if ALLOWED_IPS and request.remote_addr not in ALLOWED_IPS:
        logging.warning(f"בקשה נחסמה מ-IP לא מורשה: {request.remote_addr}")
        return ym_say_and_go_back("t-גישה נדחתה")


@app.route('/create-playfile', methods=['GET', 'POST'])
def create_playfile():
    # ---------- פרטי מערכת ----------
    system_raw = request.values.get('system')
    password_raw = request.values.get('password')
    extension = request.values.get('extension')

    # ---------- שאלות ----------
    say_length = request.values.get('say_length')
    play_beep = request.values.get('play_beep')
    play_order = request.values.get('play_order')
    say_files_amount = request.values.get('say_files_amount')
    source_extension = request.values.get('source_extension')
    source_extension_path = request.values.get('source_extension_path')
    end_action = request.values.get('end_action')
    end_extension = request.values.get('end_extension')
    last_play_action = request.values.get('last_play_action')

    if not system_raw:
        return ym_read("system", "t-אנא הקישו את מספר המערכת ובסיום הקישו סולמית", 10)
    if not password_raw:
        return ym_read("password", "t-אנא הקישו את סיסמת המערכת ובסיום הקישו סולמית", 10)
    if not extension:
        return ym_read("extension", "t-אנא הקישו את מספר השלוחה החדשה ובסיום הקישו סולמית", 10)

    # ---------- שאלה 1: אורך הקובץ ----------
    if say_length is None:
        return ym_read("say_length", "t-האם להשמיע את אורך הקובץ? 1-כן תמיד 2-רק אם ארוך מ-5 דקות 0-לא", 1)
    if say_length not in ("0", "1", "2"):
        return ym_read("say_length", "t-קלט לא תקין. האם להשמיע את אורך הקובץ? 1-כן תמיד 2-רק אם ארוך מ-5 דקות 0-לא", 1)

    # ---------- שאלה 2: ביפ ----------
    if play_beep is None:
        return ym_read("play_beep", "t-ברירת המחדל שיש ביפ (צליל) בין קבצים. להסיר את הביפ הקש 1, להשאיר ברירת מחדל הקש 0", 1)
    if play_beep not in ("0", "1"):
        return ym_read("play_beep", "t-קלט לא תקין. להסיר ביפ הקש 1, להשאיר ברירת מחדל הקש 0", 1)

    # ---------- שאלה 3: סדר השמעה ----------
    if play_order is None:
        return ym_read("play_order", "t-ברירת המחדל השמעה מהחדש לישן (max). להחליף למינימום (מהישן לחדש) הקש 1, להשאיר ברירת מחדל הקש 0", 1)
    if play_order not in ("0", "1"):
        return ym_read("play_order", "t-קלט לא תקין. להחליף סדר הקש 1, להשאיר ברירת מחדל הקש 0", 1)

    # ---------- שאלה 4: כמות הודעות ----------
    if say_files_amount is None:
        return ym_read("say_files_amount", "t-ברירת המחדל לא להשמיע את כמות ההודעות. להשמיע הקש 1, להשאיר ברירת מחדל הקש 0", 1)
    if say_files_amount not in ("0", "1"):
        return ym_read("say_files_amount", "t-קלט לא תקין. להשמיע כמות הקש 1, להשאיר ברירת מחדל הקש 0", 1)

    # ---------- שאלה 5: מקור קבצים ----------
    if source_extension is None:
        return ym_read("source_extension", "t-ברירת המחדל להשמיע מהשלוחה עצמה. להשמיע משלוחה אחרת הקש 1, להשאיר ברירת מחדל הקש 0", 1)
    if source_extension not in ("0", "1"):
        return ym_read("source_extension", "t-קלט לא תקין. להשמיע משלוחה אחרת הקש 1, להשאיר ברירת מחדל הקש 0", 1)

    if source_extension == "1" and not source_extension_path:
        return ym_read("source_extension_path", "t-אנא הקישו את מספר השלוחה המקור (לשלוחה פנימית הקישו כוכבית) ובסיום הקישו סולמית", 10)

    # ---------- שאלה 6: סיום ----------
    if end_action is None:
        return ym_read("end_action", "t-ברירת המחדל לחזור אחורה אחרי הסיום. לעבור לשלוחה אחרת הקש 1, להשאיר ברירת מחדל הקש 0", 1)
    if end_action not in ("0", "1"):
        return ym_read("end_action", "t-קלט לא תקין. לעבור לשלוחה אחרת הקש 1, להשאיר ברירת מחדל הקש 0", 1)

    if end_action == "1" and not end_extension:
        return ym_read("end_extension", "t-אנא הקישו את מספר השלוחה אליה תרצו לעבור בסיום (לשלוחה פנימית הקישו כוכבית) ובסיום הקישו סולמית", 10)

    # ---------- שאלה 7: חזרה למיקום אחרון ----------
    if last_play_action is None:
        return ym_read("last_play_action", "t-ברירת המחדל לא לשמור מיקום. לשמור עם תפריט הקש 1, אוטומטי הקש 2, להשאיר ברירת מחדל הקש 0", 1)
    if last_play_action not in ("0", "1", "2"):
        return ym_read("last_play_action", "t-קלט לא תקין. לשמור עם תפריט הקש 1, אוטומטי הקש 2, להשאיר ברירת מחדל הקש 0", 1)

    # ---------- המרת תשובות ----------
    if say_length == "1":
        say_length_value = "say_length=yes"
    elif say_length == "2":
        say_length_value = "playfile_say_length_if=5"
    else:
        say_length_value = "say_length=no"

    beep_line = "play_beep=no" if play_beep == "1" else ""
    order_line = "start=min" if play_order == "1" else ""
    files_amount_line = "say_files_amount=yes" if say_files_amount == "1" else ""

    if source_extension == "1" and source_extension_path:
        clean_source = clean_extension_path(source_extension_path)
        source_line = f"folder_to_play=/{clean_source}"
    else:
        source_line = ""

    if end_action == "1" and end_extension:
        clean_end = clean_extension_path(end_extension)
        end_line = f"playfile_end_goto=/{clean_end}"
    else:
        end_line = ""

    if last_play_action == "1":
        last_play_lines = "save_last_play=yes\nlast_play_tfr=yes"
    elif last_play_action == "2":
        last_play_lines = "save_last_play=yes\nlast_play_auto=yes"
    else:
        last_play_lines = ""

    # ===================== יצירת השלוחה =====================
    try:
        clean_ext = clean_extension_path(extension)
        if not clean_ext:
            return ym_say_and_go_back("t-שגיאה: השלוחה ריקה")

        # ניקוי system/password כדי למנוע שבירת ה-token או הזרקת פרמטרים
        system = sanitize_token_part(system_raw)
        password = sanitize_token_part(password_raw)
        if not system or not password:
            return ym_say_and_go_back("t-שגיאה: פרטי מערכת לא תקינים")

        token = f"{system}:{password}"

        ext_ini = f"""type=playfile
after_play=return
{say_length_value}
{beep_line}
{order_line}
{files_amount_line}
{source_line}
{end_line}
{last_play_lines}
"""

        # מסירים שורות ריקות
        ext_ini = "\n".join([line for line in ext_ini.splitlines() if line.strip()])

        logging.info(f"יוצר שלוחת playfile {clean_ext}")

        r1 = requests.get(
            f"{YEMOT_API_URL}UpdateExtension",
            params={
                "token": token,
                "path": f"ivr2:{clean_ext}",
                "type": "playfile"
            },
            timeout=15
        )
        logging.info(f"UpdateExtension: {r1.status_code}")

        if not (r1.status_code == 200 and '"responseStatus":"OK"' in r1.text):
            logging.error(f"UpdateExtension נכשל: {r1.text}")
            return ym_say_and_go_back("t-שגיאה ביצירת השלוחה")

        r2 = requests.post(
            f"{YEMOT_API_URL}UploadTextFile",
            params={
                "token": token,
                "what": f"ivr2:/{clean_ext}/ext.ini",
                "contents": ext_ini
            },
            timeout=15
        )
        logging.info(f"UploadTextFile: {r2.status_code}")

        if r2.status_code == 200 and '"responseStatus":"OK"' in r2.text:
            msg = f"t-שלוחת ההשמעה {clean_ext} נוצרה"
            return ym_say_and_go_back(msg)
        else:
            logging.error(f"UploadTextFile נכשל: {r2.text}")
            return ym_say_and_go_back("t-השלוחה נוצרה אך התפריט לא נטען")

    except requests.exceptions.Timeout:
        logging.exception("Timeout מול Yemot API")
        return ym_say_and_go_back("t-השרת לא הגיב, נסו שוב")
    except requests.exceptions.RequestException:
        logging.exception("שגיאת תקשורת מול Yemot API")
        return ym_say_and_go_back("t-שגיאת תקשורת, נסו שוב")
    except Exception:
        logging.exception("שגיאה כללית")
        return ym_say_and_go_back("t-שגיאה טכנית")


if __name__ == '__main__':
    # חשוב: debug=False בפרודקשן! debug=True + host 0.0.0.0 מאפשר הרצת קוד מרוחק (RCE)
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)

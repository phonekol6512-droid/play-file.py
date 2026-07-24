import re
import logging
import requests
from flask import Flask, request, make_response

app = Flask(__name__)
YEMOT_API_URL = "https://www.call2all.co.il/ym/api/"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def ym_response(content: str):
    res = make_response(content)
    res.headers["Content-Type"] = "text/plain; charset=utf-8"
    return res


def ym_read(var_name: str, prompt: str, max_digits=10):
    return ym_response(f"read={prompt}={var_name},{max_digits},12,1,Digits")


def ym_say_and_return_to_main(text: str):
    """משמיע הודעה וחוזר לתפריט הראשי (/)"""
    return ym_response(f"id_list_message={text}\ngo_to_folder=/")


@app.route('/create-playfile', methods=['GET', 'POST'])
def create_playfile():
    # ---------- פרטי מערכת ----------
    system = request.values.get('system')
    password = request.values.get('password')
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

    if not system:
        return ym_read("system", "t-אנא הקישו את מספר המערכת ובסיום הקישו סולמית", 10)
    if not password:
        return ym_read("password", "t-אנא הקישו את סיסמת המערכת ובסיום הקישו סולמית", 10)
    if not extension:
        return ym_read("extension", "t-אנא הקישו את מספר השלוחה החדשה ובסיום הקישו סולמית", 10)

    # ---------- שאלה 1: השמעת אורך הקובץ ----------
    if say_length is None:
        return ym_read("say_length", "t-האם להשמיע את אורך הקובץ? 1-כן תמיד 2-רק אם ארוך מ-5 דקות 0-לא", 1)

    # ---------- שאלה 2: ביפ בין קבצים ----------
    if play_beep is None:
        return ym_read("play_beep", "t-ברירת המחדל שיש ביפ (צליל) בין קבצים. להסיר את הביפ הקש 1, להשאיר ברירת מחדל הקש 0", 1)

    # ---------- שאלה 3: סדר השמעה ----------
    if play_order is None:
        return ym_read("play_order", "t-ברירת המחדל השמעה מהחדש לישן (max). להחליף למינימום (מהישן לחדש) הקש 1, להשאיר ברירת מחדל הקש 0", 1)

    # ---------- שאלה 4: השמעת כמות הודעות ----------
    if say_files_amount is None:
        return ym_read("say_files_amount", "t-ברירת המחדל לא להשמיע את כמות ההודעות בשלוחה. להשמיע כמות הודעות הקש 1, להשאיר ברירת מחדל הקש 0", 1)

    # ---------- שאלה 5: מקור הקבצים ----------
    if source_extension is None:
        return ym_read("source_extension", "t-ברירת המחדל להשמיע מהשלוחה עצמה. להשמיע משלוחה אחרת הקש 1, להשאיר ברירת מחדל הקש 0", 1)

    if source_extension == "1" and not source_extension_path:
        return ym_read("source_extension_path", "t-אנא הקישו את מספר השלוחה המקור (לשלוחה פנימית הקישו כוכבית בין שלוחה לשלוחה) ובסיום הקישו סולמית", 10)

    # ---------- שאלה 6: מה לעשות בסוף ההשמעה ----------
    if end_action is None:
        return ym_read("end_action", "t-ברירת המחדל לחזור אחורה אחרי סיום ההשמעה. לעבור לשלוחה אחרת הקש 1, להשאיר ברירת מחדל הקש 0", 1)

    if end_action == "1" and not end_extension:
        return ym_read("end_extension", "t-אנא הקישו את מספר השלוחה אליה תרצו לעבור בסיום (לשלוחה פנימית הקישו כוכבית בין שלוחה לשלוחה) ובסיום הקישו סולמית", 10)

    # ---------- שאלה 7: חזרה למיקום האחרון ----------
    if last_play_action is None:
        return ym_read("last_play_action", "t-ברירת המחדל לא לשמור מיקום אחרון. לשמור מיקום אחרון עם תפריט בחירה הקש 1, לחזרה אוטומטית הקש 2, להשאיר ברירת מחדל הקש 0", 1)

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
        clean_source = source_extension_path.strip().replace('*', '/').replace('-', '/').strip('/')
        source_line = f"folder_to_play={clean_source}"
    else:
        source_line = ""

    if end_action == "1" and end_extension:
        clean_end = end_extension.strip().replace('*', '/').replace('-', '/').strip('/')
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
        clean_ext = extension.strip().replace('*', '/').replace('-', '/').strip('/')
        if not clean_ext:
            return ym_say_and_return_to_main("t-שגיאה: השלוחה ריקה")

        token = f"{system.strip()}:{password.strip()}"

        # ---------- בניית קובץ התפריט ----------
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

        logging.info(f"יוצר שלוחת playfile {clean_ext} עם ההגדרות:\n{ext_ini}")

        # ---------- שלב 1: יצירת השלוחה ----------
        r1 = requests.get(
            f"{YEMOT_API_URL}UpdateExtension",
            params={
                "token": token,
                "path": f"ivr2:{clean_ext}",
                "type": "playfile"
            },
            timeout=15
        )
        logging.info(f"UpdateExtension: {r1.status_code} - {r1.text}")

        if not (r1.status_code == 200 and '"responseStatus":"OK"' in r1.text):
            return ym_say_and_return_to_main("t-שגיאה ביצירת השלוחה")

        # ---------- שלב 2: העלאת קובץ התפריט ----------
        r2 = requests.post(
            f"{YEMOT_API_URL}UploadTextFile",
            params={
                "token": token,
                "what": f"ivr2:/{clean_ext}/ext.ini",
                "contents": ext_ini
            },
            timeout=15
        )
        logging.info(f"UploadTextFile: {r2.status_code} - {r2.text}")

        # ---------- הודעת סיכום ----------
        if r2.status_code == 200 and '"responseStatus":"OK"' in r2.text:
            if say_length == "1":
                length_label = "כן (תמיד)"
            elif say_length == "2":
                length_label = "כן (רק מעל 5 דקות)"
            else:
                length_label = "לא"

            beep_label = "ללא ביפ" if play_beep == "1" else "ברירת מחדל (יש ביפ)"
            order_label = "מהישן לחדש (min)" if play_order == "1" else "ברירת מחדל (מהחדש לישן - max)"
            files_amount_label = "כן" if say_files_amount == "1" else "לא (ברירת מחדל)"
            source_label = f"משלוחה {source_extension_path.strip().replace('*', '/')}" if source_extension == "1" else "ברירת מחדל (מהשלוחה עצמה)"
            end_label = f"לשלוחה {end_extension.strip().replace('*', '/')}" if end_action == "1" else "ברירת מחדל (חזרה אחורה)"

            if last_play_action == "1":
                last_play_label = "כן (עם תפריט בחירה)"
            elif last_play_action == "2":
                last_play_label = "כן (אוטומטי)"
            else:
                last_play_label = "לא (ברירת מחדל)"

            msg = (f"t-שלוחת ההשמעה {clean_ext} נוצרה. "
                   f"אורך הקובץ: {length_label}. "
                   f"ביפ: {beep_label}. "
                   f"סדר: {order_label}. "
                   f"כמות הודעות: {files_amount_label}. "
                   f"מקור: {source_label}. "
                   f"סיום: {end_label}. "
                   f"חזרה למיקום אחרון: {last_play_label}.")
            return ym_say_and_return_to_main(msg)
        else:
            return ym_say_and_return_to_main("t-השלוחה נוצרה אך התפריט לא נטען")

    except Exception as e:
        logging.exception("שגיאה")
        return ym_say_and_return_to_main("t-שגיאה טכנית. נסה שוב")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

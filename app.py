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
    """משמיע הודעה וחוזר לתפריט הראשי"""
    return ym_response(f"id_list_message={text}\ngo_to_folder=/")


def get_param(name: str, default=None):
    """עוזר לקבל פרמטר ולהתייחס ל'' כאל None"""
    val = request.values.get(name)
    return val.strip() if val and val.strip() else default


@app.route('/create-playfile', methods=['GET', 'POST'])
def create_playfile():
    # ---------- פרטי מערכת ----------
    system = get_param('system')
    password = get_param('password')
    extension = get_param('extension')

    if not system:
        return ym_read("system", "t-אנא הקישו את מספר המערכת ובסיום הקישו סולמית", 10)
    if not password:
        return ym_read("password", "t-אנא הקישו את סיסמת המערכת ובסיום הקישו סולמית", 10)
    if not extension:
        return ym_read("extension", "t-אנא הקישו את מספר השלוחה החדשה ובסיום הקישו סולמית", 10)

    # ---------- שאלות ----------
    say_length = get_param('say_length')
    play_beep = get_param('play_beep')
    play_order = get_param('play_order')
    say_files_amount = get_param('say_files_amount')
    source_extension = get_param('source_extension')
    source_extension_path = get_param('source_extension_path')
    end_action = get_param('end_action')
    end_extension = get_param('end_extension')
    last_play_action = get_param('last_play_action')

    # שאלה 1
    if say_length is None:
        return ym_read("say_length", "t-האם להשמיע את אורך הקובץ? 1-כן תמיד 2-רק אם ארוך מ-5 דקות 0-לא", 1)

    # שאלה 2
    if play_beep is None:
        return ym_read("play_beep", "t-ברירת המחדל שיש ביפ בין קבצים. להסיר את הביפ הקש 1, להשאיר ברירת מחדל הקש 0", 1)

    # שאלה 3
    if play_order is None:
        return ym_read("play_order", "t-ברירת המחדל השמעה מהחדש לישן (max). להחליף למינימום (מהישן לחדש) הקש 1, להשאיר ברירת מחדל הקש 0", 1)

    # שאלה 4
    if say_files_amount is None:
        return ym_read("say_files_amount", "t-ברירת המחדל לא להשמיע את כמות ההודעות. להשמיע הקש 1, להשאיר ברירת מחדל הקש 0", 1)

    # שאלה 5 - מקור
    if source_extension is None:
        return ym_read("source_extension", "t-ברירת המחדל להשמיע מהשלוחה עצמה. להשמיע משלוחה אחרת הקש 1, להשאיר ברירת מחדל הקש 0", 1)

    if source_extension == "1" and not source_extension_path:
        return ym_read("source_extension_path", "t-אנא הקישו את מספר השלוחה המקור (לשלוחה פנימית הקישו כוכבית בין שלוחה לשלוחה) ובסיום הקישו סולמית", 20)

    # שאלה 6 - סיום
    if end_action is None:
        return ym_read("end_action", "t-ברירת המחדל לחזור אחורה. לעבור לשלוחה אחרת הקש 1, להשאיר ברירת מחדל הקש 0", 1)

    if end_action == "1" and not end_extension:
        return ym_read("end_extension", "t-אנא הקישו את מספר השלוחה אליה תרצו לעבור בסיום (לשלוחה פנימית הקישו כוכבית בין שלוחה לשלוחה) ובסיום הקישו סולמית", 20)

    # שאלה 7 - מיקום אחרון
    if last_play_action is None:
        return ym_read("last_play_action", "t-ברירת המחדל לא לשמור מיקום אחרון. לשמור עם תפריט (1), אוטומטי (2), ברירת מחדל (0)", 1)

    # ===================== המרת הגדרות =====================
    try:
        clean_ext = extension.strip().replace('*', '/').replace('-', '/').strip('/')
        if not clean_ext:
            return ym_say_and_return_to_main("t-שגיאה: מספר שלוחה ריק")

        token = f"{system.strip()}:{password.strip()}"

        # בניית ext.ini
        say_length_value = {
            "1": "say_length=yes",
            "2": "playfile_say_length_if=5",
        }.get(say_length, "say_length=no")

        beep_line = "play_beep=no" if play_beep == "1" else ""
        order_line = "start=min" if play_order == "1" else ""
        files_amount_line = "say_files_amount=yes" if say_files_amount == "1" else ""

        source_line = ""
        if source_extension == "1" and source_extension_path:
            clean_source = source_extension_path.strip().replace('*', '/').replace('-', '/').strip('/')
            if clean_source:
                source_line = f"folder_to_play={clean_source}"

        end_line = ""
        if end_action == "1" and end_extension:
            clean_end = end_extension.strip().replace('*', '/').replace('-', '/').strip('/')
            if clean_end:
                end_line = f"playfile_end_goto=/{clean_end}"

        if last_play_action == "1":
            last_play_lines = "save_last_play=yes\nlast_play_tfr=yes"
        elif last_play_action == "2":
            last_play_lines = "save_last_play=yes\nlast_play_auto=yes"
        else:
            last_play_lines = ""

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

        # ניקוי שורות ריקות
        ext_ini = "\n".join(line for line in ext_ini.splitlines() if line.strip())

        logging.info(f"יוצר playfile שלוחה {clean_ext}\n{ext_ini}")

        # שלב 1: יצירת השלוחה
        r1 = requests.get(
            f"{YEMOT_API_URL}UpdateExtension",
            params={"token": token, "path": f"ivr2:{clean_ext}", "type": "playfile"},
            timeout=15
        )

        if not (r1.status_code == 200 and '"responseStatus":"OK"' in r1.text):
            logging.error(f"UpdateExtension failed: {r1.text}")
            return ym_say_and_return_to_main("t-שגיאה ביצירת השלוחה")

        # שלב 2: העלאת התפריט
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

        if r2.status_code == 200 and '"responseStatus":"OK"' in r2.text:
            # הודעת סיכום
            length_label = {"1": "כן (תמיד)", "2": "כן (רק מעל 5 דקות)"}.get(say_length, "לא")
            beep_label = "ללא ביפ" if play_beep == "1" else "עם ביפ (ברירת מחדל)"
            order_label = "מהישן לחדש" if play_order == "1" else "מהחדש לישן (ברירת מחדל)"
            files_label = "כן" if say_files_amount == "1" else "לא"
            source_label = f"משלוחה {source_extension_path}" if source_extension == "1" else "השלוחה עצמה"
            end_label = f"לשלוחה {end_extension}" if end_action == "1" else "חזרה אחורה (ברירת מחדל)"
            last_label = {"1": "עם תפריט", "2": "אוטומטי"}.get(last_play_action, "לא")

            msg = (f"t-שלוחת ההשמעה {clean_ext} נוצרה בהצלחה. "
                   f"אורך: {length_label}. ביפ: {beep_label}. "
                   f"סדר: {order_label}. כמות: {files_label}. "
                   f"מקור: {source_label}. סיום: {end_label}. "
                   f"מיקום אחרון: {last_label}.")

            return ym_say_and_return_to_main(msg)
        else:
            return ym_say_and_return_to_main("t-השלוחה נוצרה אך קובץ התפריט לא נטען")

    except Exception as e:
        logging.exception("שגיאה ביצירת playfile")
        return ym_say_and_return_to_main("t-שגיאה טכנית. נסה שוב")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

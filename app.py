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
    """מחזיר read עם max_digits=10 כברירת מחדל (למניעת ניתוק)"""
    return ym_response(f"read={prompt}={var_name},{max_digits},12,1,Digits")


def ym_say_and_go_back(text: str):
    """משמיע הודעה וחוזר לתפריט הקודם"""
    return ym_response(f"id_list_message={text}")


@app.route('/create-playfile', methods=['GET', 'POST'])
def create_playfile():
    # ---------- פרטי מערכת ----------
    system = request.values.get('system')
    password = request.values.get('password')
    extension = request.values.get('extension')

    # ---------- שאלה: אורך הקובץ ----------
    say_length = request.values.get('say_length')

    if not system:
        return ym_read("system", "t-אנא הקישו את מספר המערכת ובסיום הקישו סולמית", 10)
    if not password:
        return ym_read("password", "t-אנא הקישו את סיסמת המערכת ובסיום הקישו סולמית", 10)
    if not extension:
        return ym_read("extension", "t-אנא הקישו את מספר השלוחה החדשה ובסיום הקישו סולמית", 10)

    # ---------- שאלה: השמעת אורך הקובץ ----------
    if say_length is None:
        return ym_read("say_length", "t-האם להשמיע את אורך הקובץ? 1-כן תמיד 2-רק אם ארוך מ-5 דקות 0-לא", 10)

    # ---------- המרת התשובה ----------
    if say_length == "1":
        say_length_value = "say_length=yes"
    elif say_length == "2":
        say_length_value = "playfile_say_length_if=5"
    else:
        say_length_value = "say_length=no"

    # ===================== יצירת השלוחה =====================
    try:
        clean_ext = extension.strip().replace('*', '/').replace('-', '/').strip('/')
        if not clean_ext:
            return ym_say_and_go_back("t-שגיאה: השלוחה ריקה")

        token = f"{system.strip()}:{password.strip()}"

        # ---------- בניית קובץ התפריט ----------
        ext_ini = f"""type=playfile
start=max
after_play=return
play_beep=no
{say_length_value}
"""

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
            return ym_say_and_go_back("t-שגיאה ביצירת השלוחה")

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
            msg = f"t-שלוחת ההשמעה {clean_ext} נוצרה. אורך הקובץ: {length_label}."
            return ym_say_and_go_back(msg)
        else:
            return ym_say_and_go_back("t-השלוחה נוצרה אך התפריט לא נטען")

    except Exception as e:
        logging.exception("שגיאה")
        return ym_say_and_go_back("t-שגיאה טכנית. נסה שוב")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

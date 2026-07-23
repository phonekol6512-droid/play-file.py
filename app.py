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


def ym_read(var_name: str, prompt: str, max_digits=1):
    return ym_response(f"read={prompt}={var_name},{max_digits},12,1,Digits")


def ym_say_and_return(text: str):
    """משמיע הודעה וחוזר לתפריט הראשי."""
    return ym_response(f"id_list_message={text}\nend_goto=/")


@app.route('/create-playfile', methods=['GET', 'POST'])
def create_playfile():
    # ---------- שלב 1: פרטי מערכת ----------
    system = request.values.get('system')
    password = request.values.get('password')
    extension = request.values.get('extension')

    if not system:
        return ym_read("system", "t-אנא הקישו את מספר המערכת ובסיום הקישו סולמית", 10)
    if not password:
        return ym_read("password", "t-אנא הקישו את סיסמת המערכת ובסיום הקישו סולמית", 10)
    if not extension:
        return ym_read("extension", "t-אנא הקישו את מספר השלוחה החדשה ובסיום הקישו סולמית", 10)

    # ===================== יצירת השלוחה =====================
    try:
        clean_ext = extension.strip().replace('*', '/').replace('-', '/').strip('/')
        if not clean_ext:
            return ym_say_and_return("t-שגיאה: השלוחה ריקה")

        token = f"{system.strip()}:{password.strip()}"

        # ---------- קובץ הגדרות בסיסי ----------
        ext_ini = """type=playfile
after_play=return
play_beep=no
"""

        logging.info(f"יוצר שלוחת playfile {clean_ext}")

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
            return ym_say_and_return("t-שגיאה ביצירת השלוחה")

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

        # ---------- שלב 3: הודעת סיכום ----------
        if r2.status_code == 200 and '"responseStatus":"OK"' in r2.text:
            msg = f"t-שלוחת ההשמעה {clean_ext} נוצרה בהצלחה."
            return ym_say_and_return(msg)
        else:
            return ym_say_and_return("t-השלוחה נוצרה אך קובץ ההגדרות לא נטען")

    except Exception as e:
        logging.exception("שגיאה")
        return ym_say_and_return("t-שגיאה טכנית. נסה שוב")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

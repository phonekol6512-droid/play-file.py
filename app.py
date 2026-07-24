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


def ym_say_and_go_back(text: str):
    return ym_response(f"id_list_message={text}")


@app.route('/create-playfile', methods=['GET', 'POST'])
def create_playfile():
    system = request.values.get('system')
    password = request.values.get('password')
    extension = request.values.get('extension')

    # שאלות
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
        return ym_read("system", "t-אנא הקישו את מספר המערכת#", 10)
    if not password:
        return ym_read("password", "t-אנא הקישו את סיסמת המערכת#", 10)
    if not extension:
        return ym_read("extension", "t-אנא הקישו את מספר השלוחה#", 10)

    if say_length is None:
        return ym_read("say_length", "t-אורך הקובץ? 1-כן 2-רק מעל 5 דק' 0-לא#", 1)

    if play_beep is None:
        return ym_read("play_beep", "t-להסיר ביפ? 1-כן 0-לא#", 1)

    if play_order is None:
        return ym_read("play_order", "t-סדר: 1-ישן לחדש 0-ברירת מחדל#", 1)

    if say_files_amount is None:
        return ym_read("say_files_amount", "t-להשמיע כמות הודעות? 1-כן 0-לא#", 1)

    if source_extension is None:
        return ym_read("source_extension", "t-משלוחה אחרת? 1-כן 0-לא#", 1)

    if source_extension == "1" and not source_extension_path:
        return ym_read("source_extension_path", "t-הקש את השלוחה המקור#", 10)

    if end_action is None:
        return ym_read("end_action", "t-לעבור לשלוחה בסיום? 1-כן 0-לא#", 1)

    if end_action == "1" and not end_extension:
        return ym_read("end_extension", "t-הקש את שלוחת היעד#", 10)

    if last_play_action is None:
        return ym_read("last_play_action", "t-שמירת מיקום: 1-תפריט 2-אוטומטי 0-לא#", 1)

    # המרה
    say_length_value = "say_length=yes" if say_length == "1" else "playfile_say_length_if=5" if say_length == "2" else "say_length=no"
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

    try:
        clean_ext = extension.strip().replace('*', '/').replace('-', '/').strip('/')
        if not clean_ext:
            return ym_say_and_go_back("t-שגיאה")

        token = f"{system.strip()}:{password.strip()}"

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
        ext_ini = "\n".join([line for line in ext_ini.splitlines() if line.strip()])

        r1 = requests.get(
            f"{YEMOT_API_URL}UpdateExtension",
            params={"token": token, "path": f"ivr2:{clean_ext}", "type": "playfile"},
            timeout=15
        )
        if not (r1.status_code == 200 and '"responseStatus":"OK"' in r1.text):
            return ym_say_and_go_back("t-שגיאה ביצירה")

        r2 = requests.post(
            f"{YEMOT_API_URL}UploadTextFile",
            params={"token": token, "what": f"ivr2:/{clean_ext}/ext.ini", "contents": ext_ini},
            timeout=15
        )

        if r2.status_code == 200 and '"responseStatus":"OK"' in r2.text:
            return ym_say_and_go_back(f"t-השלוחה {clean_ext} נוצרה")
        else:
            return ym_say_and_go_back("t-נכשל בהעלאה")

    except Exception as e:
        logging.exception("שגיאה")
        return ym_say_and_go_back("t-שגיאה")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

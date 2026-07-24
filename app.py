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


def ym_say_and_go_back(text: str):
    return ym_response(f"id_list_message={text}")


@app.route('/create-playfile', methods=['GET', 'POST'])
def create_playfile():
    # ---------- שלב 1: פרטי מערכת ----------
    system = request.values.get('system')
    password = request.values.get('password')
    extension = request.values.get('extension')

    # ---------- שלב 2: שאלות (נשמרות ב-hidden variables) ----------
    say_length = request.values.get('say_length')
    play_beep = request.values.get('play_beep')
    play_order = request.values.get('play_order')
    say_files_amount = request.values.get('say_files_amount')
    source_extension = request.values.get('source_extension')
    source_extension_path = request.values.get('source_extension_path')
    end_action = request.values.get('end_action')
    end_extension = request.values.get('end_extension')
    last_play_action = request.values.get('last_play_action')

    # --- שלב 1: system ---
    if not system:
        return ym_read("system", "t-אנא הקישו את מספר המערכת ובסיומה סולמית", 10)

    # --- שלב 2: password ---
    if not password:
        return ym_read("password", "t-אנא הקישו את סיסמת המערכת ובסיומה סולמית", 10)

    # --- שלב 3: extension ---
    if not extension:
        return ym_read("extension", "t-אנא הקישו את מספר השלוחה החדשה ובסיומה סולמית", 10)

    # --- שלב 4: אורך הקובץ ---
    if say_length is None:
        return ym_read("say_length", "t-האם ברצונך להגדיר שישמיע את אורך הקובץ לפני שמשמיע את הקובץ? להגדרה כברירת מחדל הקש 0 אם ברצונך שישמיע את אורך הקובץ הקש 1 אם ברצונך שישמיע את אורך הקובץ רק אם הקובץ ארוך מחמש דקות הקש 2", 1)

    # --- שלב 5: ביפ ---
    if play_beep is None:
        return ym_read("play_beep", "t-ברירת המחדל של המערכת משמיע בין קובץ לקובץ ציפצוף להמשך ללא שינוי הקש 0 להגדרה שלא ישמיע ציפצוף בין הודעה להודעה הקש 1", 1)

    # --- שלב 6: סדר השמעה ---
    if play_order is None:
        return ym_read("play_order", "t-ברירת מחדל של המערכת משמיע את הקבצים מהחדש לישן להמשך ללא שינוי הקש 0 לשינוי והגדרה שישמיע את הקבצים מהישן לחדש הקש 1", 1)

    # --- שלב 7: כמות הודעות ---
    if say_files_amount is None:
        return ym_read("say_files_amount", "t-האם ברצונך שישמיע בכניסה לשלוחה את כמות הקבצים שנמצאים בשלוחה? להגדרה כברירת מחדל הקש 0 להגדרה שישמיע את כמות הקבצים הקש 1", 1)

    # --- שלב 8: מקור ---
    if source_extension is None:
        return ym_read("source_extension", "t-ברירת המחדל של המערכת משמיע את הקבצים מהשלוחה עצמה להמשך ללא שינוי הקש 0 לשינוי והגדרה שישמיע את הקבצים משלוחה אחרת הקש 1", 1)

    if source_extension == "1" and not source_extension_path:
        return ym_read("source_extension_path", "t-הקש את השלוחה שברצונך ממנה שישמיע את הקבצים כאשר בין שלוחה לשלוחה הקש כוכבית", 10)

    # --- שלב 9: סיום ---
    if end_action is None:
        return ym_read("end_action", "t-ברירת מחדל של המערכת בסיום השמעת ההודעות חוזר לתפריט הקודם, להמשך ללא שינוי הקש 0 לשינוי והגדרה שיעבור בסיום ההשמעה לשלוחה אחרת הקש 1", 1)

    if end_action == "1" and not end_extension:
        return ym_read("end_extension", "t-אנא הקש את מספר השלוחה אליה יעבור בסיום כאשר בין שלוחה לשלוחה הקש כוכבית", 10)

    # --- שלב 10: שמירת מיקום ---
    if last_play_action is None:
        return ym_read("last_play_action", "t-ברירת המחדל של המערכת משמיע את השלוחה מחדש כל פעם להמשך ללא שינוי הקש 0 לשינוי והגדרה שיכנס לשלוחה ישאל את המאזין האם לחזור למקום האחרון אליו האזין בשלוחה הקש 1 לשינוי והגדרה שמייד יחזור למיקום האחרון אליו האזין הקש שתיים", 1)

    # --- כעת יש לנו את כל הנתונים ---
    try:
        clean_ext = extension.strip().replace('*', '/').replace('-', '/').strip('/')
        if not clean_ext:
            return ym_say_and_go_back("t-שגיאה: השלוחה ריקה")

        token = f"{system.strip()}:{password.strip()}"

        # המרת תשובות
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
        ext_ini = "\n".join([line for line in ext_ini.splitlines() if line.strip()])

        # ---------- יצירת השלוחה ----------
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

        # ---------- העלאת קובץ התפריט ----------
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
            return ym_say_and_go_back(f"t- שלוחה  {clean_ext} נוצרה בהצלחה ")
        else:
            return ym_say_and_go_back("t-שגיאה בהעלאת התפריט")

    except Exception as e:
        logging.exception("שגיאה")
        return ym_say_and_go_back("t-שגיאה טכנית")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

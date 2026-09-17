import html
import json
import re
import sqlite3
from datetime import datetime
from urllib.parse import parse_qs
from werkzeug.security import check_password_hash, generate_password_hash
from flask import (Flask,g,jsonify,redirect,make_response, render_template,render_template_string,request,session,url_for)
import traceback
from markupsafe import Markup
import os
# 상단에 import 문 추가 예시
#from m_pay_state import M_PAY_STATE_HTML
# create_db.py 관련 모듈 (환경에 맞춰 주석 해제하여 사용)
try:
    from create_db import check_and_init_db, init_database
except ImportError:

    def check_and_init_db():
        pass

    def init_database():
        pass


app = Flask(__name__, template_folder=".")
app.secret_key = "my_secret_key"

# -------------------------------------------------------------------
# 전역 변수 및 기본 설정
# -------------------------------------------------------------------
ROOM_TYPE = ["원룸","투룸","미니투룸","정투룸","주인세대","독채","상가","전세",]
ROOM_OPTION = ["TV","에어컨","냉장고","세탁기","가스렌지","인덕션렌지","디지털도어","침대","욕실거울","인터넷","안방거울","욕실장","신발장","TV장",]
TODAY = datetime.now().strftime("%Y-%m-%d")
DATE_YEAR_ARR = list(range(datetime.now().year - 1, datetime.now().year + 4))
# 1~12월 배열 정의
DATE_MONTH_ARR = list(range(1, 13))
DATABASE = "rent.db"

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def _replace(r_value: str) -> str:
    """HTML 특수문자 이스케이프 및 공백 제거"""
    if r_value is None:
        return ""
    return html.escape(str(r_value).strip(), quote=True)

# --------------------------------------------------------------
# 수정이나 새로 하우스,아디를 체크하는 함수
#---------------------------------------------------------------
@app.route("/check", methods=["GET"])
def check_duplicate():
    check_type = request.args.get("type", "").strip()
    conn = get_db()
    cursor = conn.cursor()

    if check_type == "id":
        u_id = request.args.get("u_id", "").strip()
        if not u_id:
            return make_response("empty", 200, {'Content-Type': 'text/plain; charset=utf-8'})

        cursor.execute("SELECT COUNT(*) FROM user_tb WHERE u_id = ?", (u_id,))
        row = cursor.fetchone()
        cnt = row[0] if row else 0
        
        resp_text = "exist" if cnt > 0 else "ok"
        return make_response(resp_text, 200, {'Content-Type': 'text/plain; charset=utf-8'})

    elif check_type == "house":
        house_name = request.args.get("house_name", "").strip()
        # 🌟 첫 번째 td에서 추출해서 보낸 u_id 수신
        target_uid = request.args.get("target_uid", "").strip()
        print(target_uid)
        if not house_name:
            return make_response("empty", 200, {'Content-Type': 'text/plain; charset=utf-8'})

        is_exist = False

        try:
            # 🌟 본인(u_id == target_uid) 행은 DB 조회 대상에서 제외!
            if target_uid:
                cursor.execute("""
                    SELECT h_manage FROM user_tb 
                    WHERE u_id != ? 
                      AND h_manage IS NOT NULL 
                      AND h_manage <> ''
                """, (target_uid,))
            else:
                # 신규 사용자 추가일 때는 전체 검사
                cursor.execute("""
                    SELECT h_manage FROM user_tb 
                    WHERE h_manage IS NOT NULL AND h_manage <> ''
                """)

            rows = cursor.fetchall()
            input_houses = [h.strip() for h in house_name.split(",") if h.strip()]

            # '타인'들의 h_manage 와만 중복 비교
            for row in rows:
                val = row[0] if isinstance(row, (tuple, list)) else row['h_manage']
                if val:
                    existing_houses = [h.strip() for h in str(val).split(",") if h.strip()]
                    if any(h in existing_houses for h in input_houses):
                        is_exist = True
                        break

        except Exception as e:
            print("user_tb 중복 검사 예외:", e)

        resp_text = "exist" if is_exist else "ok"
        return make_response(resp_text, 200, {'Content-Type': 'text/plain; charset=utf-8'})

    return make_response("error", 200, {'Content-Type': 'text/plain; charset=utf-8'})

 
def _houses( u_id, house_name="") -> str:
    """사용자가 관리 권한을 가진 주택 목록 드롭다운"""
   # tb = "user_tb"
    conn = get_db()
    if not u_id:
        return (
            "<select id='opt_house' class='wid_100px' name='opt_house'>"
            "<option value=''>로그인하기</option>"
            "</select>"
        )

    cursor = conn.cursor()

    try:
        cursor.execute(
            f"SELECT h_manage FROM user_tb WHERE u_id = ?",
            (u_id,)
        )
        row = cursor.fetchone()

    finally:
        cursor.close()

    html_out = [
        "<select id='opt_house' "
        "class='wid_100px' "
        "name='opt_house' "
        "onchange='house_onchange(this.value)'>"
    ]

    html_out.append("<option value='선택'>선택</option>")

    if row and row["h_manage"]:

        h_array = [
            h.strip()
            for h in str(row["h_manage"]).split(",")
            if h.strip()
        ]

        for val in h_array:

            sel = (
                "selected"
                if house_name != "" and house_name == val
                else ""
            )

            html_out.append(
                f"<option value='{_replace(val)}' {sel}>"
                f"{_replace(val)}"
                "</option>"
            )

    html_out.append("</select>")

    return "".join(html_out)

def _rooms_type(rooms_type_arr=None, temp="") -> str:
    # 1. 인자가 문자열이거나 None/빈값이면 기본 ROOM_TYPE 리스트 사용
    if isinstance(rooms_type_arr, str) or not rooms_type_arr:
        rooms_type_arr = ROOM_TYPE

    html_out = ["<select name='rooms_type' onchange='room_type_onchange()'>"]
    
    # 2. 선택 안내문구(temp)가 있을 때만 기본 option 추가
    if temp:
        html_out.append(f"<option value=''>{_replace(temp)}</option>")
    else:
        html_out.append("<option value=''>선택</option>")

    # 3. 리스트 순회하여 option 태그 생성
    for i, ss in enumerate(rooms_type_arr):
        html_out.append(f"<option value='{i}'>{_replace(ss)}</option>")

    html_out.append("</select>")
    return "".join(html_out)

def _load_room(house_name, room_num, value) -> str:\

    conn = get_db()
    cursor = conn.cursor()

    try:
        sql = """
            SELECT p_room_num
            FROM p_room_info_tb
            WHERE p_room_state=? AND p_house_name=?
        """
        cursor.execute(sql, (value, house_name))
        rows = cursor.fetchall()
    finally:
        cursor.close()

    safe_house_name = _replace(house_name)

    # p 값에 따라 onchange 결정
    if str(value) == "2":
        select_tag = (
            f"<select class='wid_80px' name='opt_num' "
            f"onchange=\"num_room_onchange('{safe_house_name}', this.value)\">"
        )

    elif str(value) == "3":
        select_tag = (
            "<select class='wid_80px' name='opt_num'>"
        )

    elif str(value) == "4":
        select_tag = (
            f"<select class='wid_80px' name='opt_num' "
            f"onchange=\"num_pay_onchange('{safe_house_name}', this.value)\">"
        )

    else:
        select_tag = (
            "<select class='wid_80px' name='opt_num'>"
        )

    html_out = [select_tag]

    html_out.append("<option value='선택'>룸선택</option>")

    for row in rows:
        p_num = str(row["p_room_num"])
        sel = " selected" if str(room_num) == p_num else ""

        html_out.append(
            f"<option value='{_replace(p_num)}'{sel}>"
            f"{_replace(p_num)}</option>"
        )

    html_out.append("</select>")

    return "".join(html_out)
def load_room_info_add(house_name, selected_room_num="") -> str:
    # ==========================================================
    # 1. DB 연결
    # ==========================================================
    try:
        conn = g.db if hasattr(g, 'db') and g.db is not None else get_db()
        cursor = conn.cursor()

    except Exception as e:
        print(f"[load_room_info_add] DB 연결 에러: {e}")

        return Markup(
            "<select class='wid_80px' id='opt_num' name='opt_num'>"
            "<option value='선택'>DB오류</option>"
            "</select>"
        )

    html_out = []

    # ==========================================================
    # 2. 현재 페이지 p 값
    # ==========================================================
    p = str(request.args.get("p", ""))

    print("====================================")
    print("[load_room_info_add]")
    print("p =", p)
    print("house_name =", repr(house_name))
    print("selected_room_num =", repr(selected_room_num))
    print("====================================")

    # ==========================================================
    # 3. 주택 이름 HTML 안전 처리
    # ==========================================================
    safe_house_name = html.escape(
        str(house_name or "").strip(),
        quote=True
    )

    # ==========================================================
    # 4. p 값에 따른 select 이벤트 설정
    # ==========================================================

    if p == "2":

        # p=2 : 룸정보 등록
        # 미등록 호실 선택
        html_out.append(
            f"<select class='wid_80px' id='opt_num' name='opt_num' "
            f"onchange=\"num_room_onchange('{safe_house_name}', this.value);\">\n"
        )

    elif p == "3":

        # p=3 : 룸정보 수정
        # 등록된 호실만 표시
        html_out.append(
            f"<select class='wid_80px' id='opt_num' name='opt_num' "
            f"onchange=\"num_room_onchange('{safe_house_name}', this.value);\">\n"
        )

    elif p == "4":

        # p=4 : 결제/상태 화면
        # 전체 호실 표시
        html_out.append(
            f"<select class='wid_80px' id='opt_num' name='opt_num' "
            f"onchange=\"num_pay_onchange('{safe_house_name}', this.value);\">\n"
        )

    else:

        html_out.append(
            f"<select class='wid_80px' id='opt_num' name='opt_num'>\n"
        )

    # 기본 선택
    html_out.append(
        "<option value='선택'>선택</option>\n"
    )

    

    registered_rooms = set()

    if house_name:

        try:

            cursor.execute(
                """
                SELECT p_room_num
                FROM p_room_info_tb
                WHERE p_house_name = ?
                """,
                (house_name,)
            )

            registered_rows = cursor.fetchall()

            for row in registered_rows:

                try:
                    registered_room = row["p_room_num"]

                except (KeyError, TypeError, IndexError):

                    registered_room = row[0]

                if registered_room is not None:

                    registered_rooms.add(
                        str(registered_room).strip()
                    )

        except Exception as e:

            print(
                f"[load_room_info_add] "
                f"등록 호실 조회 에러: {e}"
            )

    print(
        "[load_room_info_add] "
        f"현재 등록된 호실 = {registered_rooms}"
    )

    # ==========================================================
    # 6. house_tb에서 전체 호실 가져오기
    # ==========================================================

    try:

        if house_name:

            sql = """
                SELECT m_room_all
                FROM house_tb
                WHERE m_house_name = ?
            """

            cursor.execute(
                sql,
                (house_name,)
            )

            rows = cursor.fetchall()

            # ==================================================
            # 7. house_tb의 전체 호실 처리
            # ==================================================

            for row in rows:

                # ----------------------------------------------
                # sqlite3.Row / dict / tuple 대응
                # ----------------------------------------------

                try:
                    house_room_num = row["m_room_all"]

                except (KeyError, TypeError, IndexError):

                    house_room_num = row[0]

                if not house_room_num:
                    continue

                

                house_room_num_arr = [
                    r.strip()
                    for r in str(house_room_num).split(",")
                    if r.strip()
                ]

                # ==================================================
                # 8. 전체 호실을 하나씩 검사
                # ==================================================

                for room in house_room_num_arr:

                    room = str(room).strip()

                    

                    if p == "2":

                        if room in registered_rooms:

                            print(
                                f"[p=2] "
                                f"이미 등록된 호실 제외 → {room}"
                            )

                            continue

                    

                    elif p == "3":

                        if room not in registered_rooms:
                        
                            print(
                                f"[p=3] "
                                f"등록되지 않은 호실 제외 → {room}"
                            )

                            continue

                    

                    elif p == "4":

                        pass

                    

                    else:

                        try:

                            if _check_room_rent_state(
                                house_name,
                                room
                            ) == "1":

                                continue

                        except Exception as chk_e:

                            print(
                                f"[_check_room_rent_state 에러]: "
                                f"{chk_e}"
                            )

                    # ==================================================
                    # 9. 현재 선택된 호실 selected 처리
                    # ==================================================

                    selected = (
                        " selected"
                        if str(room) == str(selected_room_num)
                        else ""
                    )

                    # ==================================================
                    # 10. HTML 안전 처리
                    # ==================================================

                    safe_room = html.escape(
                        str(room),
                        quote=True
                    )

                    # ==================================================
                    # 11. option 생성
                    # ==================================================

                    html_out.append(
                        f"<option value='{safe_room}'{selected}>"
                        f"{safe_room}"
                        f"</option>\n"
                    )

    except Exception as e:

        print(
            f"[load_room_info_add 상세 에러]: {e}"
        )

        traceback.print_exc()

    # ==========================================================
    # 12. select 종료
    # ==========================================================

    html_out.append(
        "</select>\n"
    )

    # ==========================================================
    # 13. HTML 반환
    # ==========================================================

    return Markup(
        "".join(html_out)
    )


    


def _get_renter_name(house_name, room_num):
    cursor = g.db.cursor()
    try:
        sql = "SELECT pr_name FROM room_private_tb WHERE house_name=? AND room_num=?"
        cursor.execute(sql, (house_name, room_num))
        row = cursor.fetchone()
        if row:
            return row["pr_name"] if "pr_name" in row.keys() else ""
    finally:
        cursor.close()
    return ""


def _get_renter_ipkum_water(house_name, room_num):
    cursor = g.db.cursor()
    try:
        sql = "SELECT water_ck FROM room_ipkum_tb WHERE house_name=? AND room_num=?"
        cursor.execute(sql, (house_name, room_num))
        row = cursor.fetchone()
        if row:
            return row["water_ck"] if "water_ck" in row.keys() else ""
    finally:
        cursor.close()
    return ""


def _get_sum_ipkum_total(house_name, room_num):
    cursor = g.db.cursor()
    try:
        sql = "SELECT SUM(ipkum_won) as total FROM room_ipkum_tb WHERE house_name=? AND room_num=?"
        cursor.execute(sql, (house_name, room_num))
        row = cursor.fetchone()
        if row and row["total"] is not None:
            return int(row["total"])
    finally:
        cursor.close()
    return 0


def _get_month_sum(start_date: str):
    if not start_date:
        return "0개월"
    try:
        start = datetime.strptime(str(start_date), "%Y%m%d")
        now = datetime.now()
        months = (now.year - start.year) * 12 + (now.month - start.month)
        if now.day > start.day:
            months += 1
        return f"{max(0, months)}개월"
    except ValueError:
        return "0개월"


def _get_rent_month_won(house_name, room_num):
    return _get_room_rent_price(house_name, room_num)


def _minab(house_name, room_num, start_date):
    month_str = _get_month_sum(start_date)
    months_digits = re.sub(r"[^0-9]", "", month_str)
    months = int(months_digits) if months_digits else 0

    rent = _get_rent_month_won(house_name, room_num)
    total_ipkum = _get_sum_ipkum_total(house_name, room_num)

    unpaid = (months * rent) - total_ipkum
    return f"{unpaid:,}"


def _get_room_rent_price(house_name, room_num):
    cursor = g.db.cursor()
    try:
        sql = "SELECT p_room_month_won FROM p_room_info_tb WHERE p_room_num = ? AND p_house_name = ? LIMIT 1"
        cursor.execute(sql, (room_num, house_name))
        row = cursor.fetchone()
        if row and row["p_room_month_won"] is not None:
           value = row["p_room_month_won"]

           if value is None or str(value).strip() == "":
              return 0

           return int(str(value).replace(",", "").strip())
    finally:
        cursor.close()
    return 0


def _check_room_rent_state(house_name, room_num):
    cursor = g.db.cursor()
    try:
        sql = "SELECT p_room_state FROM p_room_info_tb WHERE p_room_num=? AND p_house_name=? LIMIT 1"
        cursor.execute(sql, (room_num, house_name))
        row = cursor.fetchone()
        if row and "p_room_state" in row.keys():
            return str(row["p_room_state"])
    finally:
        cursor.close()
    return "0"


def rent_state_str(value):
    return "임대중" if str(value) == "1" else "공실"


@app.context_processor
def utility_processor():
    return dict(
        load_room_info_add=load_room_info_add,
        pay_load_room_info=pay_load_room_info,
        _houses=_houses,
        _rooms_type=_rooms_type,
        rooms_type=_rooms_type,
        ROOM_OPTION=ROOM_OPTION,
        room_options=ROOM_OPTION,
    )

# -------------------------------------------------------------
# 내장 HTML 템플릿 변수 (HTML_PAGE)
# -------------------------------------------------------------

HTML_PAGE = """

<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>임대 관리 시스템</title>
    <link rel="stylesheet" href="static/css/style.css">
</head>
<body>

<table class="menu-choos" width="100%">
    <tr>
        {% if p == '1' or p == 1 %}
            <th class="menu-choos rounded-th_over">주택등록</th>
            <th class="bg-menu rounded-th"><a href="/?p=2" title="룸정보 등록">룸정보등록</a></th>
            <th class="bg-menu rounded-th"><a href="/?p=3" title="임차인등록">임차인등록</a></th>
            <th class="bg-menu rounded-th"><a href="/?p=4" title="입금등록">입금등록</a></th>

        {% elif p == '2' or p == 2 %}
            <th class="bg-menu rounded-th"><a href="/?p=1" title="주택등록">주택등록</a></th>
            <th class="menu-choos rounded-th_over">룸정보등록</th>
            <th class="bg-menu rounded-th"><a href="/?p=3" title="임차인등록">임차인등록</a></th>
            <th class="bg-menu rounded-th"><a href="/?p=4" title="입금등록">입금등록</a></th>

        {% elif p == '3' or p == 3 %}
            <th class="bg-menu rounded-th"><a href="/?p=1" title="주택등록">주택등록</a></th>
            <th class="bg-menu rounded-th"><a href="/?p=2" title="룸정보 등록">룸정보등록</a></th>
            <th class="menu-choos rounded-th_over">임차인등록</th>
            <th class="bg-menu rounded-th"><a href="/?p=4" title="입금등록">입금등록</a></th>

        {% elif p == '4' or p == 4 %}
            <th class="bg-menu rounded-th"><a href="/?p=1" title="주택등록">주택등록</a></th>
            <th class="bg-menu rounded-th"><a href="/?p=2" title="룸정보 등록">룸정보등록</a></th>
            <th class="bg-menu rounded-th"><a href="/?p=3" title="임차인등록">임차인등록</a></th>
            <th class="menu-choos rounded-th_over">입금등록</th>
        {% endif %}
    </tr>
</table>

{% if msg %}
<script>
    alert("{{ msg }}");
</script>
{% endif %}
<!--=======================================================-->
<!--#manage.php-->
<!--#===================================================-->
{% if session.get('user') == current_master or session.get('master') == current_master %}
    <!-- 1. 처음에는 숨겨져 있다가 [사용자관리] 버튼을 누르면 열리는 컨테이너 -->
    <div id="manage_container" style="display: none;">
       <!-- 회원 목록 테이블 -->
<table class="menu-choos">
    <tr>
        <td>ID</td>
        <td>관리대상 및 설정</td>
        <td>삭제</td>
    </tr>

    {% for row in users %}
    <tr class="bg-room">
        <td class="wid_60px">{{ row.u_id }}</td>

        <td>
        <form action="" method="post" style="margin:0; display:inline;">
        <input type="hidden" name="update_id" value="{{ row.id_num }}">
        <!-- 입력창 -->
        <input type="text" class="align_box" name="h_manage" value="{{ row.h_manage or '' }}"
               oninput="this.size = Math.max(5, this.value.length + 1); var btn = this.closest('tr').querySelector('button[type=submit]'); if(btn) btn.disabled = true;" 
               style="width: auto; min-width: 40px;">
        
        <select name="update_lebel" class="wid_40px">
            {% for i in range(1, 6) %}
                <option value="{{ i }}" {% if row.u_lebel|string == i|string %}selected{% endif %}>{{ i }}</option>
            {% endfor %}
        </select>

        <!-- 🌟 클릭된 버튼 자신(this)을 전달 -->
        <button type="button" class="align_box" onclick="runCheck(this.form);">체크</button>
        
        <!-- 🌟 수정 버튼 (기본 disabled) -->
        <button type="submit" class="align_box" disabled>수정</button>
        </form>
        </td>

        <td>
            {% if row.u_id != current_master %}
                <a href="?delete={{ row.id_num }}" 
                   onclick="return confirm('등록된 모든 데이터가 삭제됨 삭제하시겠습니까?')">X</a>
            {% else %}
                -
            {% endif %}
        </td>
    </tr>
    {% endfor %}
</table>

        <!-- 사용자 추가 폼 -->
        <form name="frm_add" id="frm_add" method="post">
            <table>
                <tr>
                    <td colspan="2" class="wid_120px" align="center">
                        ID <input type="text" name="u_id" id="u_id">
                        관리대상 <input type="text" name="h_manage" id="h_manage">
                        PW <input type="text" name="u_pw" id="u_pw">
                    </td>
                </tr>
                <tr>
                    <td class="wid_120px" align="center">
                        <input type="button" value="ID체크" name="btn_id_check" onclick="user_id_check();">
                        <input type="button" value="주택 중복체크" name="btn_house_add" onclick="house_name_check();">
                        <input type="button" value="사용자추가" name="btn_login" onclick="user_add();" disabled>
                    </td>
                </tr>
            </table>
        </form>
    </div>

    
{% endif %}


<form name="frm_login" id="frm_login" method="post">
    <table class="bg-room">
        {% if session.get('user') %}
            <tr class="menu-choos">
                <td align="center"><strong>메뉴</strong></td>
            </tr>
            <tr>
                <td>
                    {{ session.get('master') or session.get('user') }} 접속중...
                    <input type="button" value="로그아웃" onclick="user_logout();">
                     <button type="button"  id="manage_btn"  onclick="toggleManage()">  사용자관리     </button>
                </td>
            </tr>
            
        {% else %}
            <tr class="menu-choos"><td align="center"><strong>로그인</strong></td></tr>
            <tr>
                <td>
                    <label for="u_id">ID</label>
                    <input type="text" class="wid_80px" name="u_id" id="u_id">
                    
                    <label for="u_pw">PW</label>
                    <input type="password" id="u_pw" name="u_pw" placeholder="*********" onkeyup="if(event.key === 'Enter'){ login(); }">
                    <span id="toggleBtn" class="toggle-text" onclick="togglePassword()">T</span>
                    
                    <input type="button" value="로그인" name="btn_login" onclick="login();">
                </td>
            </tr>
        {% endif %}
    </table>
</form>

{% if p == '1' or p == 1 or not p %}
    <form name="frm_house_info" method="post" action="">
        <table class="bg-room">
            <tr class="menu-choos">
                <td colspan="2" align="center">관리할 주택을 등록합니다</td>
            </tr>
            <tr>
                <td align="center" colspan="2">
                    <input class="input_long" type="button" value="주택 등록">
                </td>
            </tr>
            <tr>
                  <td class="wid_20px">관리할대상</td>
                  <td class="wid_100px">
                     {{ houses_select_html | safe }}
                  </td>
            </tr>
            <tr>
                <td class="wid_20px">주인이름</td>
                <td><input class="wid_100px" type="text" name="m_name"></td>
            </tr>
            <tr>
                <td class="wid_20px">주인전화</td>
                <td>
                    <input class="wid_120px" type="text" inputmode="numeric" name="m_phone">-없이 입력
                </td>
            </tr>
            <tr>
                <td class="wid_20px">주소</td>
                <td><input class="wid_100" type="text" name="m_address"></td>
            </tr>
            <tr>
                <td class="wid_20px">각호이름</td>
                <td><input class="wid_100" type="text" inputmode="numeric" name="m_room_all"></td>
            </tr>
            <tr>
                <td align="center" colspan="2">하우스 전체 호실을 등록 (101,102,103,201,,,)</td>
            </tr>
            <tr>
                <td align="center" class="font+size_M" colspan="2">
                    <input class="wid_60px" type="button" name="btn_renter_add" value="등록" onclick='frmsubmit_house("add");'>
                    <input class="wid_60px" type="button" name="btn_renter_cancel" value="취소" onclick='house_add_cancel();'>
                    <input class="wid_60px" type="button" name="btn_renter_del" value="삭제" onclick='house_del_submit();'>
                    <input class="wid_100px button_style" type="button" name="btn_edit" value="수정" onclick='frmsubmit_house("edit");'>
                </td>
            </tr>
        </table>
    </form>

    <table class="bg-room">
        <tr class="menu-choos">
            <td class="font+size_S menu-choos">수정선택(주택 이름 클릭), E(임대정보 수정), X(임대정보 삭제)</td>
        </tr>
        <tr>
            <td>
                <table>
                    <tr class="menu-choos">
                        <td class="bg-menu">주택이름</td>
                        <td class="bg-menu">관리자 이름</td>
                        <td class="bg-menu">전화번호</td>
                        <td class="bg-menu">X</td>
                    </tr>
                   <!-- p=1 테이블 출력 영역 -->
{% if house_info_list %}
    {% for row in house_info_list %}
    <tr>
        <td>
            <a href="#" title="수정하기" onclick="house_info_load('{{ row.id_num }}', '{{ row.m_house_name }}', '{{ row.m_address }}', '{{ row.m_room_all }}', '{{ row.m_name }}', '{{ row.m_phone }}'); return false;">
                {{ row.m_house_name }}
            </a>
        </td>
        <td>{{ row.m_name }}</td>
        <td>{{ row.m_phone }}</td>
        <td>
            <a href="#" onclick="house_del('{{ row.m_house_name }}', '{{ row.id_num }}'); return false;" title="삭제하기">X</a>
        </td>
    </tr>
    {% endfor %}
{% else %}
    <!-- 주택이 선택되지 않아 num_rows == 0 일 때 -->
    <tr>
        <td colspan="4" style="text-align:center;">주택을 선택해 주세요.</td>
    </tr>
{% endif %}

<tr>
    <td colspan="4">주택이름을 클릭하면 수정할 수 있습니다.</td>
</tr>
                </table>
            </td>
        </tr>
    </table>

{% elif p == '2' or p == 2 %}
    <!-- 각 룸 정보 등록 시작 -->
<form name="frm_rent_info" method="post" action="">
    <table class="bg-room">
        <tr>
            <td class="menu-choos" colspan="2">임대상황(E(임대정보수정),X(임대대정보삭제))</td>
        </tr>
        
        <input type="hidden" name="f_type">
        <input type="hidden" name="id_num">
        <input type="hidden" name="r_num">
        
        <tr>
            <td align="center" colspan="2"><input type="button" value="룸세부등록"></td>
        </tr>
         <tr>
                        <td class="wid_30px">주택선택</td>
                        <td class="wid_80px">
                          {{ houses_select_html | safe }}
                          방호수
                          {{ load_room_info_add(house_name, room_num) | safe }}
                        </td>
        </tr>
        
        <tr>
            <td class="wid_40px">룸타입</td>
            <td>{{ _rooms_type(room_type, "") | safe }}</td>
        </tr>
        <tr>
            <td class="wid_40px">보증금</td>
            <td><input type="text" class="wid_150px money" name="p_room_bo" onKeyPress="fncChk(this.value,1);">원</td>
        </tr>
        <tr>
            <td class="wid_40px">임대료</td>
            <td class="wid_150px"><input type="text" class="wid_150px money" name="p_room_month_won" onKeyPress="fncChk(this.value,1);">원</td>
        </tr>
        <tr>
            <td class="wid_40px">옵션</td>
            <td class="wid_200px">
                <!-- _room_opt_check() 대체 -->
                {% for opt in ROOM_OPTION %}
                    {% if loop.index0 % 3 == 0 and not loop.first %}<br>{% endif %}
                    <input class="wid_20px" type="checkbox" name="ck[{{ loop.index0 }}]" value="true"> {{ opt }}
                {% endfor %}
            </td>
        </tr>

        <tr>
            <td colspan="2" align="center">
                <input class="wid_60px" type="button" name="btn_add" value="등 록" onclick="room_add('add');">
                <input class="wid_60px" type="button" name="btn_edit" value="수 정" onclick="room_add('edit');">
                <input class="wid_60px" type="button" name="btn_cancel" value="취 소" onclick="room_cancel();">
            </td>
        </tr>
    </table>
</form>

<table class="bg-room">
    <tr>
        <td colspan="6" class="font+size_S">임대상황(E(임대정보수정),X(임대정보삭제))</td>
    </tr>
    <tr>
        <td class="bg-menu">주택이름</td>
        <td class="bg-menu">호수</td>
        <td class="bg-menu">보증금</td>
        <td class="bg-menu">월임대료</td>
        <td class="bg-menu">상황</td>
        <td class="bg-menu">X</td>
    </tr>

    <!-- _rent_state() 대체 -->
    {% for row in rent_room_list %}
    <tr bgcolor="white">
        <td>{{ row.p_house_name }}</td>
        <td>
            <a href="#" onclick="rent_roomnumber_click('{{ row.id_num }}', '{{ row.p_house_name }}', '{{ row.p_room_num }}', '{{ row.p_room_type }}', '{{ row.p_room_month_won }}', '{{ row.p_room_bo }}', '{{ row.p_room_option }}')" title="수정하기">
                {{ row.p_room_num }}
            </a>
        </td>
        <td>{{ row.p_room_bo }}</td>
        <td>{{ row.p_room_month_won }}</td>
        <td>{{ row.room_state_str }}</td>
        <td>
            <a href="#" onclick="del_house_room('{{ row.p_house_name }}', '{{ row.p_room_num }}', '{{ row.id_num }}')" title="삭제하기">X</a>
        </td>
    </tr>
    {% else %}
    <tr>
        <td colspan="6">등록된 호실 정보가 없습니다.</td>
    </tr>
    {% endfor %}

    <tr>
        <td colspan="6">주택호수를 클릭하면 수정가능합니다.</td>
    </tr>
</table>

{% elif p == '3' or p == 3 %}
    <!-------------------------- 임차인 등록 / 수정 폼 ---------------------------->
    <form name="frm_renter_add" method="post" action="/rent_write?p=3&f_type=room_renter_edit">
        <input type="hidden" name="house_name" value="{{ house_name }}">
        <input type="hidden" name="room_num" value="{{ room_num }}">
        
        <table class="bg-room">
            <tr class="menu-choos">
                <td colspan="2" align="center">임차등록(E(임차정보수정),X(임차정보삭제))</td>
            </tr>
            <tr>
                <td align="center" colspan="2">
                    <input type="button" name="btn_renter_temp" value="임차인 등록">
                </td>
            </tr>
            <tr>
                <td class="wid_30px">주택선택</td>
                <td class="wid_80px">
                  {{ houses_select_html | safe }}
                  
                  {{ load_room_info_add(house_name, room_num) | safe }}
                </td>
            </tr>
            <tr>
                <td class="wid_30px">이름</td>
                <td class="wid_80px">
                    <input class="wid_100px" type="text" name="txt_renter_name">
                    전화 <input type="text" class="wid_120px" name="txt_renter_phone" onkeypress="return event.charCode >= 48 && event.charCode <= 57">
                </td>
            </tr>
            <tr>
                <td class="wid_30px">주소</td>
                <td><input class="wid_100" type="text" name="txt_renter_address"></td>
            </tr>
            <tr>
                <td class="wid_30px">주민번호</td>
                <td>
                    <input type="text" class="wid_80px" name="txt_renter_pnum1" onkeypress="return event.charCode >= 48 && event.charCode <= 57"> -
                    <input class="wid_80px" type="text" name="txt_renter_pnum2" onkeypress="return event.charCode >= 48 && event.charCode <= 57">
                </td>
            </tr>
            <tr>
                <td class="wid_30px">E-Mail</td>
                <td><input class="wid_100" type="text" name="txt_renter_email"></td>
            </tr>
            <tr>
                <td align="center" colspan="2">
                    <input type="button" name="renter_add" value="저장" onclick="rent_private_submit();">
                    <input type="button" name="renter_edit" value="수정" onclick="room_renter_edit_onclick();">
                    <input type="button" name="renter_cancel" value="취소" onclick="cancel();">
                </td>
            </tr>
        </table>
    </form>

    <!-- 임차인 목록 테이블 (_renter_state() 변환) -->
    <table class="bg-room">
        <tr class="menu-choos">
            <td class="bg-menu">주택이름</td>
            <td class="bg-menu">호수</td>
            <td class="bg-menu">이름</td>
            <td class="bg-menu">전화</td>
            <td class="bg-menu">X</td>
        </tr>

        {% for row in renter_info_list %}
        <tr>
            <td bgcolor="white">
                <div class="clickable-cell" onclick="showPopup('{{ row.house_name }}||{{ row.room_num }}')" style="cursor:pointer;">
                    {{ row.house_name }}
                </div>
            </td>
            <td bgcolor="white">
                <a href="#" onclick="renter_roomnumber_click('{{ row.house_name }}', '{{ row.room_num }}', '{{ row.pr_name }}', '{{ row.pr_address }}', '{{ row.pr_email }}', '{{ row.pr_phone }}', '{{ row.pr_number }}')" title="수정하기클릭">
                    {{ row.room_num }}
                </a>
            </td>
            <td bgcolor="white">{{ row.pr_name }}</td>
            <td bgcolor="white">{{ row.pr_phone }}</td>
            <td bgcolor="white">
                <a href="#" onclick="delete_room('{{ row.room_num }}', '{{ row.pr_name }}');" title="임차인삭제하기">X</a>
            </td>
        </tr>
        {% else %}
        <tr>
            <td colspan="5" bgcolor="white" align="center">
                {% if house_name %}
                    등록된 임차인 정보가 없습니다.
                {% else %}
                    주택을 선택해 주세요.
                {% endif %}
            </td>
        </tr>
        {% endfor %}

        <tr>
            <td colspan="5">주택이름을 클릭하면 계약서를 인쇄할 수 있습니다.</td>
        </tr>
    </table>

{% elif p == '4' or p == 4 %}
    <!---------------------------- 룸 입금 등록 테이블 시작 -------------------------------->

<!----------------------룸등록시작----------------------------------->
<table class="bg-room">
    <tr class="menu-choos">
        <td colspan="5">입금등록, E(수정), X(삭제)</td>
    </tr>
    <tr>
        <td class="wid_30px">주택선택</td>
        <td colspan="4" class="wid_80px">
            {{ houses_select_html | safe }}
             
            {{ load_room_info_add(house_name, room_num) | safe }}
           
               {{ _date_year(s_date) | safe}}년
           
        </td>
     </tr>
    <tr class="bg-menu"> 
        <td class="wid_80px">날  짜</td>
        <td class="wid_80px">금  액</td>
        <td class="wid_80px">입금자</td>
        <td class="wid_30px">수  도</td>
        <td> X</td>
    </tr>
    {{ pay_load_num_field() | safe }}
</table>

<table class="bg-room">
    {{ pay_load_room_info(house_name, s_date) | safe  }}
</table>
<!----------------------룸등록시작끝----------------------------------->


{% endif %}

<script src="{{ url_for('static', filename='js/script.js') }}"></script>
</body>
</html>
"""


# -------------------------------------------------------------
# 라우트 제어
# -------------------------------------------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    conn = get_db()
    cursor = conn.cursor()

    # 1. 회원 권한 및 관리대상 수정 (POST)
    if request.method == "POST" and "update_id" in request.form:
        id_num = int(request.form["update_id"])
        manage = request.form.get("h_manage", "")
        level = request.form.get("update_lebel", "")

        cursor.execute(
            "UPDATE user_tb SET u_lebel = ?, h_manage = ? WHERE id_num = ?",
            (level, manage, id_num)
        )
        conn.commit()
        session["msg"] = "수정되었습니다."
        return redirect("/")

    # 2. 회원 삭제 및 연관 데이터 연쇄 삭제 (GET query parameter)
    delete_id = request.args.get("delete")
    if delete_id and delete_id.isdigit():
        id_num = int(delete_id)

        # 삭제 대상의 h_manage 가져오기
        cursor.execute("SELECT h_manage FROM user_tb WHERE id_num = ?", (id_num,))
        user_tb = cursor.fetchone()

        if user_tb:
            h_manage_str = user_tb["h_manage"] or ""
            # 쉼표(,)로 구분된 관리대상 파싱
            manage_list = [m.strip() for m in h_manage_str.split(",") if m.strip()]
            # tables = ['house_tb', 'p_room_info_tb', 'room_private_tb', 'room_ipkum_tb', 'room_outkum_tb']
            tables = ['room_private_tb', 'room_ipkum_tb', 'room_outkum_tb']
            # 연관 테이블 삭제
            for m in manage_list:
       
               cursor.execute("DELETE FROM house_tb WHERE m_house_name = ?", (m,))
        
               cursor.execute("DELETE FROM p_room_info_tb WHERE p_house_name = ?", (m,))
        
               for table in tables:
                    cursor.execute(f"DELETE FROM {table} WHERE house_name = ?", (m,))
                    cursor.execute("DELETE FROM user_tb WHERE id_num = ?", (id_num,))

        conn.commit()
        cursor.execute("DELETE FROM user_tb WHERE id_num = ?", (id_num,))
        return redirect("/")
    p = request.args.get("p", "1")
    house_name = request.args.get("house_name", "")
    room_num = request.args.get("room_num", "")
    msg = session.pop("msg", None)
    u_id = session.get("user")

    houses_select_html = _houses(u_id, house_name)

    house_info_list = []
    rent_room_list = []
    renter_info_list = []

    # p=1: 주택 등록 화면 데이터
    if p in ["1", 1, "0", 0]:
        try:
            house_name1 = request.args.get("house_name", "")
            
            if not house_name1 or house_name1 in ["선택", "%EC%84%A0%ED%83%9D"]:
                house_info_list = []
            else:
                cursor.execute(
                    "SELECT * FROM house_tb WHERE m_house_name = ?", (house_name1,)
                )
                house_info_list = cursor.fetchall()
        except sqlite3.OperationalError:
            house_info_list = []

    # p=2: 룸 정보 등록 화면 데이터 조회
    elif p in ["2", 2]:
        try:
            house_name1 = request.args.get("house_name", "").strip()

            print("====================================")
            print("p =", repr(p))
            print("house_name1 =", repr(house_name1))
            print("u_id =", repr(u_id))
            print("====================================")

            rent_room_list = []

            if not u_id or not house_name1 or house_name1 == "선택":
                print("주택명이 없거나 선택 상태입니다.")
            else:
                cursor.execute(
                    """
                    SELECT *
                    FROM p_room_info_tb
                    WHERE p_house_name = ?
                    ORDER BY p_room_num
                    """,
                    (house_name1,)
                )

                rows = cursor.fetchall()

                print("조회된 룸 개수 =", len(rows))

                for row in rows:
                    rent_room_list.append({
                        "id_num": row["id_num"],
                        "p_house_name": row["p_house_name"],
                        "p_room_num": row["p_room_num"],
                        "p_room_type": row["p_room_type"],
                        "p_room_month_won": row["p_room_month_won"],
                        "p_room_bo": row["p_room_bo"],
                        "p_room_option": (
                            row["p_room_option"]
                            if "p_room_option" in row.keys()
                            else ""
                        ),
                        "room_state_str": rent_state_str(
                            row["p_room_state"]
                            if row["p_room_state"] is not None
                            else "0"
                        )
                    })

                print("rent_room_list =", rent_room_list)

        except sqlite3.OperationalError as e:
            print("SQLite OperationalError:", e)
            rent_room_list = []

        except Exception as e:
            print("룸 정보 조회 오류:", e)
            rent_room_list = []

    # p=3: 임차인 등록 화면 데이터 추가
    elif p in ["3", 3]:
        renter_info_list = get_renter_state_list(house_name)

    # p=4: 입금/방 정보 화면 데이터 추가
    elif str(p) == "4":
        s_date = request.args.get('s_date', '').strip()
        room_num = request.args.get('room_num', '').strip()
        
        pay_room_html = pay_load_room_info(house_name=house_name, s_date=s_date)   

    # -------------------------------------------------------------
    # 최고관리자인 경우 회원 목록 조회
    # -------------------------------------------------------------
    users = []
    if session.get("master") == "최고관리자":
        cursor.execute("SELECT * FROM user_tb ORDER BY id_num")
        users = cursor.fetchall()

    # 로그인한 최고관리자 계정 확인용 (필요시 사용)
    current_master = session.get("master")

    # -------------------------------------------------------------
    # HTML 문자열 템플릿 렌더링 반환
    # -------------------------------------------------------------
    return render_template_string(
        HTML_PAGE,
        p=p,
        msg=msg,
        get_db=get_db,

        _date_year=_date_year,
        _date_month=_date_month,

        house_name=house_name,
        room_num=room_num,

        houses_select_html=houses_select_html,

        house_info_list=house_info_list if 'house_info_list' in locals() else [],
        rent_room_list=rent_room_list if 'rent_room_list' in locals() else [],
        renter_info_list=renter_info_list if 'renter_info_list' in locals() else [],

        pay_room_html=pay_room_html if 'pay_room_html' in locals() else "",

        load_room_info_add=load_room_info_add,
        pay_load_num_field=pay_load_num_field,

        # 🌟 회원 관리용 변수 전달
        users=users,
        current_master=current_master,
    )
# =============================================================
# 1. Write 액션 라우팅 핸들러 (반드시 라우터 함수보다 위에 위치!)
# =============================================================

@app.route("/rent_write", methods=["GET", "POST"])
def handle_rent_write():
    # GET/POST 파라미터 수신 (PHP의 $_REQUEST['f_type'] 대응)
    f_type = request.args.get("f_type") or request.form.get("f_type") or ""

    if f_type == "check_id":
        return user_login()
    elif f_type == "log_out":
        return log_out()
    elif f_type == "user_add":
        return user_add()
    elif f_type == "user_edit":
        return user_edit()
    elif f_type == "house_add":
        return house_add()
    elif f_type == "house_edit":
        return house_edit()
    elif f_type in ["house_del", "ipkum_delete", "room_private_delete", "room_delete", "house_room_delete", "outkum_delete"]:
        return _delete(f_type)
    elif f_type == "ipkum_add":
        return ipkum_add()
    elif f_type == "ipkum_edit":
        return ipkum_edit()
    elif f_type == "ipkum_auto_add":
        return ipkum_auto_add()
    elif f_type == "room_add":
        return room_add()
    elif f_type == "room_edit":
        return room_edit()
    elif f_type == "renter_add":
        return renter_add()
    elif f_type == "room_renter_edit":
        return renter_edit()
    else:
        session["msg"] = "함수가 없거나 잘못된 요청입니다."
        return redirect(request.referrer or "/")

# -------------------------------------------------------------------
# 회원 및 로그인 관련 처리
# -------------------------------------------------------------------
def user_login():
    conn = get_db()
    cursor = conn.cursor()

    login_id = _replace(request.form.get("u_id") or request.args.get("u_id"))
    login_pw = request.form.get("u_pw") or request.args.get("u_pw") or ""

    if not login_id or not login_pw:
        session["msg"] = "아이디와 비밀번호를 입력해 주세요."
        return redirect(request.referrer or "/")

    try:
        cursor.execute("SELECT * FROM user_tb WHERE u_id = ?", (login_id,))
        row = cursor.fetchone()

        if row and check_password_hash(row["u_pw"], login_pw):
            session["user"] = login_id
            u_lebel = str(row["u_lebel"]).strip()

            if u_lebel == "1":
                session["master"] = "최고관리자"
            elif u_lebel == "2":
                session["master"] = f"{login_id}관리자"
            else:
                session["master"] = "GUEST"

            return redirect(request.referrer or "/")

        session["msg"] = "아이디 또는 비밀번호가 일치하지 않습니다."
        return redirect(request.referrer or "/")

    except Exception as e:
        session["msg"] = f"로그인 처리 중 에러 발생: {e}"
        return redirect(request.referrer or "/")


def log_out():
    session.clear()
    session["master"] = ""
    return redirect("/")


def user_add():
    u_id = _replace(request.form.get("u_id"))
    u_pw = request.form.get("u_pw") or ""
    h_manage = _replace(request.form.get("h_manage"))

    if not u_id or not u_pw:
        session["msg"] = "사용자 ID와 비밀번호를 입력하세요."
        return redirect(request.referrer or "/")

    conn = get_db()
    cursor = conn.cursor()
    hashed_pw = generate_password_hash(u_pw)
    level = "5"

    try:
        cursor.execute(
            "INSERT INTO user_tb (u_id, h_manage, u_pw, u_lebel) VALUES (?, ?, ?, ?)",
            (u_id, h_manage, hashed_pw, level),
        )
        conn.commit()
        session["msg"] = "사용자가 성공적으로 등록되었습니다."
    except Exception as e:
        session["msg"] = f"user_tb 데이터 저장 실패: {e}"

    return redirect(request.referrer or "/")


def user_edit():
    u_id = _replace(request.form.get("u_id"))
    u_pw = request.form.get("u_pw") or ""
    h_manage = _replace(request.form.get("h_manage"))
    u_lebel = _replace(request.form.get("u_lebel"))

    conn = get_db()
    cursor = conn.cursor()
    hashed_pw = generate_password_hash(u_pw)

    try:
        cursor.execute(
            "UPDATE user_tb SET u_pw = ?, u_lebel = ?, h_manage = ? WHERE u_id = ?",
            (hashed_pw, u_lebel, h_manage, u_id),
        )
        conn.commit()
        session["msg"] = "사용자 정보가 수정되었습니다."
    except Exception as e:
        session["msg"] = f"user_tb 데이터 수정 실패: {e}"

    return redirect(request.referrer or "/")


# -------------------------------------------------------------------
# 1. 주택(하우스) 관리 처리
# -------------------------------------------------------------------
from flask import jsonify

@app.route("/api/get_rooms", methods=["GET"])
def api_get_rooms():
    house_name = request.args.get("house_name", "").strip()
    
    if not house_name or house_name == "선택":
        return jsonify({"success": False, "rooms": []})

    conn = get_db()
    cursor = conn.cursor()
    available_rooms = []

    try:
        cursor.execute("SELECT m_room_all FROM house_tb WHERE m_house_name = ?", (house_name,))
        row = cursor.fetchone()

        if row and row["m_room_all"]:
            # 쉼표(,)로 구분된 호실 번호 분할
            rooms = [r.strip() for r in str(row["m_room_all"]).split(",") if r.strip()]
            
            for room in rooms:
                # 이미 임대 중인 방('1')은 제외하고 미임대 호실만 담기
                if _check_room_rent_state(house_name, room) != "1":
                    available_rooms.append(room)

        return jsonify({"success": True, "rooms": available_rooms})

    except Exception as e:
        print(f"API 호실 조회 에러: {e}")
        return jsonify({"success": False, "rooms": []})
    finally:
        cursor.close()

def house_add():
   
    conn = get_db()
    cursor = conn.cursor()

    opt_house = _replace(request.form.get("opt_house"))

    if not opt_house or opt_house == "선택":
        session["msg"] = "등록할 주택 이름을 입력하거나 선택하세요."
        return redirect(request.referrer or "/")

    cursor.execute(
        "SELECT COUNT(*) as cnt FROM house_tb WHERE m_house_name = ?",
        (opt_house,),
    )
    count = cursor.fetchone()["cnt"]

    if count == 0:
        cursor.execute(
            """INSERT INTO house_tb (m_house_name, m_address, m_room_all, m_name, m_phone, m_date)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                opt_house,
                _replace(request.form.get("m_address")),
                _replace(request.form.get("m_room_all")),
                _replace(request.form.get("m_name")),
                _replace(request.form.get("m_phone")),
                TODAY,
            ),
        )
        conn.commit()
        session["msg"] = "주택이 등록되었습니다."
    else:
        session["msg"] = "이미 존재해 있는 같은 이름의 주택입니다."

    return redirect(request.referrer or "/")
def house_edit():
    conn = get_db()
    cursor = conn.cursor()

    opt_house = _replace(request.form.get("opt_house"))

    try:
        cursor.execute(
            """UPDATE house_tb SET m_address = ?, m_room_all = ?, m_name = ?, m_phone = ?
               WHERE m_house_name = ?""",
            (
                _replace(request.form.get("m_address")),
                _replace(request.form.get("m_room_all")),
                _replace(request.form.get("m_name")),
                _replace(request.form.get("m_phone")),
                opt_house,
            ),
        )
        conn.commit()
        session["msg"] = "주택 정보가 수정되었습니다."
    except Exception as e:
        session["msg"] = f"주택 수정 실패: {e}"

    return redirect(request.referrer or "/")


# -------------------------------------------------------------------
# 2. 룸(호실) 정보 관리 처리
# -------------------------------------------------------------------

@app.route("/m_rent_room_add")
def m_rent_room_add():
    conn = get_db()
    house_name = request.args.get("house_name", "")
    room_num = request.args.get("room_num", "")
    s_date = request.args.get("s_date", "")
    p = request.args.get("p", "2")

    # 1. 백엔드에서 HTML을 미리 렌더링해서 문자열 변수로 보낼 때
    room_info_html = load_room_info_add(house_name, room_num)

    # 2. HTML_PAGE 변수로 전달
    return render_template_string(
        HTML_PAGE,
        s_date=s_date,
        house_name=house_name,
        room_num=room_num,
        p=p,
        room_info=room_info_html,
        _date_year=_date_year,
        _date_month=_date_month,
        load_room_info_add=load_room_info_add,
        #load_num_field=load_num_field
    )

def room_opt_check(room_option_ck):
    for i, ss in enumerate(room_option_ck):
        # 0이 아니면서 3의 배수일 때 줄바꿈 태그 출력
        if i % 3 == 0 and i != 0:
            print("<br>")
            
        print(f"<input class='wid_20px' type='checkbox' name='ck[{i}]' value='true'> {ss} ")

        
def _set_room_option():
    selected = []
    # ROOM_OPTION 배열의 전체 개수(len)만큼 반복
    for i in range(len(ROOM_OPTION)):
        val = request.form.get(f"ck[{i}]") or request.form.get(f"ck_{i}")
        if val:
            selected.append(str(i))
    return ",".join(selected)

def rent_option_str(value):
   
    # 1. 쉼표 기준 분할 및 공백 제거, 숫자 요소만 필터링 후 정수 변환
    indices = [
        int(item.strip())
        for item in value.split(",")
        if item.strip().isdigit()
    ]

    # 2. 오름차순 정렬
    indices.sort()

    # 3. room_option 존재 여부 확인 후 값 추출
    str_opt_list = []
    for index in indices:
        # dict 키 존재 여부나 list 인덱스 범위를 체크
        if (
            isinstance(ROOM_OPTION, dict) and index in ROOM_OPTION
        ) or (
            isinstance(ROOM_OPTION, list) and 0 <= index < len(ROOM_OPTION)
        ):
            str_opt_list.append(str(ROOM_OPTION[index]))

    # 4. 쉼표로 연결하여 반환 (rtrim 효과)
    return ",".join(str_opt_list)


def room_add():
    # today = datetime.now().strftime("%Y-%m-%d")
    conn = get_db()
    cursor = conn.cursor()

    opt_house = _replace(request.form.get("opt_house"))
    p_room_num = _replace(request.form.get("opt_num"))
    p_rooms_type = _replace(request.form.get("rooms_type"))
    p_room_bo = _replace(request.form.get("p_room_bo"))
    p_room_month_won = _replace(request.form.get("p_room_month_won"))
    p_room_option = _set_room_option()

    if not p_room_num or p_room_num == "선택":
        session["msg"] = "방 번호를 선택해 주세요."
        return redirect(request.referrer or "/")

    cursor.execute(
        "SELECT COUNT(*) as cnt FROM p_room_info_tb WHERE p_house_name = ? AND p_room_num = ?",
        (opt_house, p_room_num),
    )
    if cursor.fetchone()["cnt"] == 0:

        # ------------------ [터미널 출력 추가] ------------------
        print("=" * 40)
        print("[DB INSERT] 등록할 방 정보:")
        print(f" - 건물명(p_house_name)   : {opt_house}")
        print(f" - 호수(p_room_num)       : {p_room_num}")
        print(f" - 방 타입(p_room_type)   : {p_rooms_type}")
        print(f" - 보증금(p_room_bo)      : {p_room_bo}")
        print(f" - 월세(p_room_month_won) : {p_room_month_won}")
        print(f" - 옵션(p_room_option)    : {p_room_option}")
        print(f" - 등록일(p_date)         : {TODAY}")
        print("=" * 40)
    # -----------------------------------------------------



        cursor.execute(
            """INSERT INTO p_room_info_tb 
               (p_house_name, p_room_num, p_room_type, p_room_bo, p_room_month_won, p_room_option, p_room_state, p_date)
               VALUES (?, ?, ?, ?, ?, ?, '0', ?)""",
            (
                opt_house,
                p_room_num,
                p_rooms_type,
                p_room_bo,
                p_room_month_won,
                p_room_option,
                TODAY,
            ),
        )
        conn.commit()
        session["msg"] = "룸 정보가 등록되었습니다."
    else:
        session["msg"] = "이미 등록되어 있는 방 정보입니다."

    return redirect(request.referrer or "/")


def room_edit():
    conn = get_db()
    cursor = conn.cursor()

    id_num = _replace(request.form.get("id_num"))
    p_house_name = _replace(request.form.get("opt_house"))
    p_room_num = _replace(request.form.get("r_num"))
    p_rooms_type = _replace(request.form.get("rooms_type"))
    p_room_bo = _replace(request.form.get("p_room_bo"))
    p_room_month_won = _replace(request.form.get("p_room_month_won"))
    p_room_option = _set_room_option()

    try:
        cursor.execute(
            """UPDATE p_room_info_tb 
               SET p_house_name = ?, p_room_type = ?, p_room_bo = ?, p_room_option = ?, p_room_month_won = ?
               WHERE id_num = ? AND p_room_num = ?""",
            (
                p_house_name,
                p_rooms_type,
                p_room_bo,
                p_room_option,
                p_room_month_won,
                id_num,
                p_room_num,
            ),
        )
        conn.commit()
        session["msg"] = "룸 정보가 수정되었습니다."
    except Exception as e:
        session["msg"] = f"룸 정보 수정 실패: {e}"

    return redirect(request.referrer or "/")


# -------------------------------------------------------------------
# 3. 임차인 정보 관리 처리
# -------------------------------------------------------------------

def _set_room_rent_state(house_name, room_num, st_value):
    """
    p_room_info_tb 테이블의 방 임대 상태(p_room_state)를 업데이트합니다.
    :param house_name: 주택 이름
    :param room_num: 호실 번호
    :param st_value: 상태 값 ('0': 공실, '1': 임대 중 등)
    :return: 성공 시 True, 실패 시 False
    """
    try:
        conn = get_db()
        cursor = conn.cursor()

        sql = """
            UPDATE p_room_info_tb 
            SET p_room_state = ? 
            WHERE p_room_num = ? AND p_house_name = ?
        """
        
        # SQL 실행 (파라미터 순서: st_value -> room_num -> house_name)
        cursor.execute(sql, (str(st_value), str(room_num), str(house_name)))
        conn.commit()
        
        return True
    except Exception as e:
        print(f"[_set_room_rent_state] DB 업데이트 오류: {e}")
        return False
    finally:
        cursor.close()

def renter_add():
    # today = datetime.now().strftime("%Y-%m-%d")
    conn = get_db()
    cursor = conn.cursor()

    txt_house_name = _replace(request.form.get("opt_house"))
    txt_room_num = _replace(request.form.get("opt_num"))
    txt_renter_name = _replace(request.form.get("txt_renter_name"))
    txt_renter_pnum = _replace(
        request.form.get("txt_renter_pnum1", "")
    ) + _replace(request.form.get("txt_renter_pnum2", ""))
    txt_renter_phone = _replace(request.form.get("txt_renter_phone"))
    txt_renter_address = _replace(request.form.get("txt_renter_address"))
    txt_renter_email = _replace(request.form.get("txt_renter_email"))

    try:
        cursor.execute(
            """INSERT INTO room_private_tb
               (room_num, house_name, pr_name, pr_number, pr_phone_num, pr_address, pr_email, pr_rent_start, pr_rent_end)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                txt_room_num,
                txt_house_name,
                txt_renter_name,
                txt_renter_pnum,
                txt_renter_phone,
                txt_renter_address,
                txt_renter_email,
                TODAY,
                TODAY,
            ),
        )
        conn.commit()

        # 방 상태를 임대 중('1')으로 업데이트
        _set_room_rent_state(txt_house_name, txt_room_num, "1")
        session["msg"] = "임차인 정보가 등록되었습니다."
    except Exception as e:
        session["msg"] = f"임차인 등록 실패: {e}"

    return redirect(request.referrer or "/")


def renter_edit():
    # today = datetime.now().strftime("%Y-%m-%d")
    conn = get_db()
    cursor = conn.cursor()

    txt_house_name = _replace(request.form.get("house_name"))
    txt_room_num = _replace(request.form.get("room_num"))
    txt_renter_name = _replace(request.form.get("txt_renter_name"))
    txt_renter_pnum = _replace(
        request.form.get("txt_renter_pnum1", "")
    ) + _replace(request.form.get("txt_renter_pnum2", ""))
    txt_renter_phone = _replace(request.form.get("txt_renter_phone"))
    txt_renter_address = _replace(request.form.get("txt_renter_address"))
    txt_renter_email = _replace(request.form.get("txt_renter_email"))

    try:
        cursor.execute(
            """UPDATE room_private_tb
               SET pr_name = ?, pr_number = ?, pr_phone_num = ?, pr_address = ?, pr_email = ?, pr_rent_start = ?, pr_rent_end = ?
               WHERE room_num = ? AND house_name = ?""",
            (
                txt_renter_name,
                txt_renter_pnum,
                txt_renter_phone,
                txt_renter_address,
                txt_renter_email,
                TODAY,
                TODAY,
                txt_room_num,
                txt_house_name,
            ),
        )
        conn.commit()

        _set_room_rent_state(txt_house_name, txt_room_num, "1")
        session["msg"] = "임차인 정보가 수정되었습니다."
    except Exception as e:
        session["msg"] = f"임차인 수정 실패: {e}"

    return redirect(request.referrer or "/")

# -------------------------------------------------------------------
# _renter_state 함수 파이썬 변환
# -------------------------------------------------------------------
def get_renter_state_list(house_name=""):
    """선택된 주택의 임차인 목록을 DB에서 조회하여 반환"""
    if not house_name or house_name == "선택":
        return []

    conn = get_db()
    cursor = conn.cursor()
    renter_list = []

    try:
        sql = "SELECT * FROM room_private_tb WHERE house_name = ? ORDER BY room_num"
        cursor.execute(sql, (house_name,))
        rows = cursor.fetchall()

        for row in rows:
            renter_list.append({
                "house_name": str(row["house_name"] or ""),
                "room_num": str(row["room_num"] or ""),
                "pr_name": str(row["pr_name"] or ""),
                "pr_phone": str(row["pr_phone_num"] or ""),
                "pr_rent_start": str(row["pr_rent_start"] or ""),
                "pr_number": str(row["pr_number"] or ""),
                "pr_address": str(row["pr_address"] or ""),
                "pr_email": str(row["pr_email"] or ""),
            })
    except Exception as e:
        print(f"renter_state 조회 오류: {e}")
    finally:
        cursor.close()

    return renter_list


# -------------------------------------------------------------------
# 4. 입금 정보 관리 처리pay_state
# -------------------------------------------------------------------
def ipkum_add():
    conn = get_db()
    cursor = conn.cursor()

    try:
        house_name = _replace(request.form.get("house_name", ""))
        room_num = _replace(request.form.get("room_num", ""))
        ipkum_gita = _replace(request.form.get("ipkum_gita", "")) or "없음"

        # [수정된 핵심 부분]
        # value='1'로 설정되어 있으므로 '1' 또는 'on'일 때 1, 체크 안 하면 0
        water_val = request.form.get("water_ck")
        water_ck = 1 if water_val in ["1", "on"] else 0
        print("==========================입금등록")
        print("[POST Form Data]", request.form)
        print("water_ck RAW value =", repr(request.form.get("water_ck")))
        print("==================================입금등록")
        if str(_check_room_rent_state(house_name, room_num)) == "1":
            sql = """
                INSERT INTO room_ipkum_tb 
                (house_name, room_num, ipkum_day, ipkum_name, ipkum_won, ipkum_gita, water_ck)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(
                sql,
                (
                    house_name,
                    room_num,
                    _replace(request.form.get("ipkum_date", "")),
                    _replace(request.form.get("ipkum_name", "")),
                    _replace(request.form.get("ipkum_won", "")),
                    ipkum_gita,
                    water_ck,
                ),
            )
            conn.commit()
            session["msg"] = "입금 내역이 등록되었습니다."
        else:
            session["msg"] = "해당 방은 현재 임대 중이 아닙니다."

    finally:
        cursor.close()
        conn.close()

    return redirect(request.referrer or "/")

def ipkum_edit():
    conn = get_db()
    cursor = conn.cursor()

    id_num = _replace(request.form.get("id_num"))
    house_name = _replace(request.form.get("house_name"))
    room_num = _replace(request.form.get("room_num"))
    ipkum_gita = _replace(request.form.get("ipkum_gita")) or "없음"
    # water_ck = 1 if request.form.get("water_ck") == "on" else 0
    water_val = request.form.get("water_ck")
    water_ck = 1 if water_val in ["1", "on"] else 0
    print("======================================")
    print("[POST Form Data]", request.form)
    print("water_ck RAW value =", repr(request.form.get("water_ck")))
    print("======================================입금수정")
    if _check_room_rent_state(house_name, room_num) == "1":
        print("======================================입금수정2")
        cursor.execute(
            """UPDATE room_ipkum_tb SET
               house_name = ?, room_num = ?, ipkum_day = ?, ipkum_name = ?, ipkum_won = ?, ipkum_gita = ?, water_ck = ?
               WHERE id_num = ?""",
            (
                house_name,
                room_num,
                _replace(request.form.get("ipkum_date")),
                _replace(request.form.get("ipkum_name")),
                _replace(request.form.get("ipkum_won")),
                ipkum_gita,
                water_ck,
                id_num,
            ),
        )
        conn.commit()
        session["msg"] = "입금 내역이 수정되었습니다."
    else:
        session["msg"] = "해당 방은 현재 임대 중이 아닙니다."

    return redirect(request.referrer or "/")


def ipkum_auto_add():
    # TODAY가 파일 상단에 없다면 아래 주석을 해제하여 사용
    # TODAY = datetime.now().strftime("%Y-%m-%d")

    conn = get_db()
    cursor = conn.cursor()

    # GET 요청(request.args) 방식으로 들어오므로 파라미터를 안전하게 수신
    house_name = _replace(request.args.get("house_name", ""))
    room_num = _replace(request.args.get("room_num", ""))
    ipkum_won = _replace(request.args.get("ipkum_won", "")) or "0"
    ipkum_name = _replace(request.args.get("ipkum_name", ""))
    ipkum_gita = _replace(request.args.get("ipkum_gita", "")) or "없음"

    # GET 요청에 맞춰 request.args로 변경 (값이 '1' 또는 'on'이면 1)
    water_ck = 1 if request.args.get("water_ck") in ["1", "on"] else 0

    try:
        if str(_check_room_rent_state(house_name, room_num)) == "1":
            print("======================================")
            print("[ipkum_auto_add]")
            print("house_name =", house_name)
            print("room_num   =", room_num)
            print("ipkum_won  =", ipkum_won)
            print("ipkum_name =", ipkum_name)
            print("======================================")

            sql = """
                INSERT INTO room_ipkum_tb 
                (house_name, room_num, ipkum_day, ipkum_name, ipkum_won, ipkum_gita, water_ck)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(
                sql,
                (
                    house_name,
                    room_num,
                    TODAY,
                    ipkum_name,
                    ipkum_won,
                    ipkum_gita,
                    water_ck,
                ),
            )
            conn.commit()
            session["msg"] = "자동 입금 내역이 등록되었습니다."
        else:
            session["msg"] = "임대 중인 방이 아니어서 입금 등록이 취소되었습니다."

    finally:
        # DB 연결 자원 해제
        cursor.close()
        conn.close()

    return redirect(request.referrer or "/")

# -------------------------------------------------------------------
# m_pay_state
# -------------------------------------------------------------------
@app.route("/m_pay_state")
def m_pay_state():
    u_id = session.get('user')
    
    house_name = request.args.get("house_name", "").strip()
    room_num = request.args.get("room_num", "").strip()
    s_date = request.args.get("s_date", "").strip()
    p = request.args.get("p", "4")

    conn = get_db()

    houses_select_html = _houses( u_id, house_name)

    room_info_html = pay_load_room_info(house_name=house_name,s_date=s_date)

    return render_template_string(
    HTML_PAGE,
    house_name=house_name,
    room_num=room_num,
    s_date=s_date,
    p=p,
    room_info=room_info_html,
    houses_select_html=houses_select_html,
    _date_year=_date_year,
    _date_month=_date_month,
    load_room_info_add=load_room_info_add,
    pay_load_room_info=pay_load_room_info,
    pay_load_num_field=pay_load_num_field,
    )

from markupsafe import Markup



def pay_load_room_info(house_name,s_date):
    conn = get_db()
    cursor = conn.cursor()
    if not s_date: s_date = str(datetime.now().year)
    clean_s_date = str(s_date).replace("-", "").replace("_", "")
    snb = "house_tb"

    # 1. 건물 정보 및 방 목록 조회
    sql = f"SELECT * FROM {snb} WHERE m_house_name = ?"
    cursor.execute(sql, (house_name,))
    rows = cursor.fetchone()

    rooms_num_arr = []
    if rows:
        try:
            m_room_all = rows["m_room_all"]
        except (KeyError, TypeError, IndexError):
            m_room_all = rows[0]

        if m_room_all:
            rooms_num_arr = str(m_room_all).split(",")

    html_out = []

    # 2. 방 호수 헤더 출력
    # html_out.append("<tr><td class='bg-menu'>월&#65340;호</td>\n")
    html_out.append("<tr><td class='bg-menu'></td>\n")
    for room in rooms_num_arr:
        html_out.append(f"<td class='bg-menu' colspan='2'>{room}</td>\n")
    html_out.append("</tr>\n\n")

    # 3. 월별/방별 입금 상태 루프
    for idx, month_day in enumerate(DATE_MONTH_ARR):
        disp_month = f"{int(month_day):02d}"
        html_out.append(f"<tr><td align=center class='wid_20px'>{month_day}</td>\n")

        for r_num in rooms_num_arr:
            search_date = f"{clean_s_date}{disp_month}%"

            sql_ipkum = """
                SELECT * FROM room_ipkum_tb
                WHERE house_name = ? AND room_num = ?
                  AND REPLACE(REPLACE(ipkum_day, '-', ''), '_', '') LIKE ?
            """
            cursor.execute(sql_ipkum, (house_name, r_num, search_date))
            rs_data = cursor.fetchall()

            rs = rs_data[0] if len(rs_data) > 0 else None

            if rs:
                try:
                    ipkum_won = rs["ipkum_won"]
                except (KeyError, TypeError, IndexError):
                    ipkum_won = rs[0]

                if ipkum_won != "" and ipkum_won is not None:
                    rs1 = list(rs_data)
                    rs2 = list(rs_data)

                    html_out.append(
                        f"<td class='wid_20px'>{load_ipkum_sum(rs1)}</td>\n"
                    )
                    html_out.append(
                        f"<td class='wid_20px'>{load_ipkum_sum_del(rs2)}</td>\n"
                    )
            else:
                r_name = _get_renter_name(house_name, r_num)
                r_price = _get_room_rent_price(house_name, r_num)
                room_ck = _check_room_rent_state(house_name, r_num)

                if str(room_ck) == "0":
                    html_out.append(
                        "<td colspan=2><input class='wid_30px' type='button' value='공실' style='background-color: #FFBB00;'></td>"
                    )
                else:
                    html_out.append("<td colspan=2>")
                    html_out.append(
                        f"<input class='wid_40px' type='button' value='{month_day}' "
                        f"onclick=\"auto_ipkum_add('{house_name}', '{r_num}', '{r_name}', '{r_price}');\" "
                        f"style='background-color: #E4F7BA; cursor: pointer;'>\n"
                    )
                    html_out.append("</td>\n")

        html_out.append("</tr>\n\n")

    # 4. 하단 합계 표 레이아웃
    room_count = len(rooms_num_arr)
    html_out.append(
        f"<tr><td colspan={room_count * 2}>각월에 있는 'E' 수정 'X' 는 삭제</td></tr>"
    )
    html_out.append(f"<tr><td colspan={room_count * 2}></td></tr>\n\n")
    html_out.append("<tr><td>\n")
    html_out.append("<table>\n")
    html_out.append("<tr><td>수</td></tr>\n")
    html_out.append("<tr><td>총</td></tr>\n")
    html_out.append("<tr><td>미</td></tr>\n")
    html_out.append("</table>\n")
    html_out.append("</td>\n")

    for r_num in rooms_num_arr:
        html_out.append("<td colspan=2>\n")
        html_out.append("<table>\n")

        sum_html = load_sum_ipkum(house_name, r_num)
        html_out.append(str(sum_html or ""))

        html_out.append("</table>\n")
        html_out.append("</td>\n")

    html_out.append("</tr>\n")
    html_out.append("</table></td>\n\n")

    return Markup("".join(html_out))





    
def _get_ipkum_won(room_num, house_name):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT p_room_month_won FROM p_room_info_tb WHERE p_house_name=? AND p_room_num=?",
            (house_name, room_num)
        )
        row = cursor.fetchone()
        return row["p_room_month_won"] if row and row["p_room_month_won"] else 0
    except Exception:
        return 0


def minab_sum(pr_rent_start, room_num, house_name):
    try:
        std = _get_month_sum(pr_rent_start) if '_get_month_sum' in globals() else 0
        rent_won = _get_ipkum_won(room_num, house_name)
        ipkum_tot = _get_sum_ipkum_total(house_name, room_num) if '_get_sum_ipkum_total' in globals() else 0

        std = float(std) if str(std).replace('.', '', 1).isdigit() else 0
        rent_won = float(rent_won) if str(rent_won).replace('.', '', 1).isdigit() else 0
        ipkum_tot = float(ipkum_tot) if str(ipkum_tot).replace('.', '', 1).isdigit() else 0

        return (std * rent_won) - ipkum_tot
    except Exception:
        return 0


def load_ipkum_sum(rows_list):
    """입금 수정(E) 버튼 생성"""
    html_out = []
    for row in rows_list:
        ipkum_won = str(row["ipkum_won"] or "")
        water_ck = str(row["water_ck"] if "water_ck" in row.keys() else "")
        
        id_num = html.escape(str(row["id_num"]), quote=True)
        ipkum_day_full = html.escape(str(row["ipkum_day"]), quote=True)
        house_name = html.escape(str(row["house_name"]), quote=True)
        room_num = html.escape(str(row["room_num"]), quote=True)
        ipkum_won_esc = html.escape(ipkum_won, quote=True)
        water_ck_esc = html.escape(water_ck, quote=True)

        renter_name = _get_renter_name(house_name, room_num) if '_get_renter_name' in globals() else ""
        renter_name_esc = html.escape(str(renter_name), quote=True)

        html_out.append(
            f"<button type='button' onclick=\"load_ipkum_data_edit('{id_num}','{ipkum_day_full}','{house_name}','{room_num}','{renter_name_esc}','{ipkum_won_esc}','{water_ck_esc}')\" title='입금정보수정'>E</button>\n"
        )
    return "".join(html_out)


def load_ipkum_sum_del(rows_list):
    """입금 삭제(X) 버튼 생성"""
    html_out = []
    for row in rows_list:
        id_num = html.escape(str(row["id_num"]), quote=True)
        html_out.append(f"<button type='button' onclick=\"delete_ipkum('{id_num}');\" title='삭제하기'>X</button>\n")
    return "".join(html_out)


def load_sum_ipkum(house_name, room_num):
    """하단 수/총/미 합계 테이블 행 생성"""
    conn = get_db()
    cursor = conn.cursor()
    html_out = []

    try:
        cursor.execute(
            "SELECT * FROM room_private_tb WHERE house_name=? AND room_num=?",
            (house_name, room_num)
        )
        rows = cursor.fetchall()
        for row in rows:
            pr_rent_start = row["pr_rent_start"]
            month_sum = _get_month_sum(pr_rent_start) if '_get_month_sum' in globals() else 0
            tot = _get_sum_ipkum_total(house_name, room_num) if '_get_sum_ipkum_total' in globals() else 0

            html_out.append(f"<tr><td>{month_sum}</td></tr>\n")
            html_out.append(f"<tr><td>{tot:,.0f}</td></tr>\n")
    except Exception as e:
        print(f"load_sum_ipkum 오류: {e}")

    return "".join(html_out)


# -------------------------------------------------------------------
# -------------------------------------------------------------------
# 메인 변환 함수 2: pay_load_num_field (하단 월별 입금 현황 매트릭스)
# -------------------------------------------------------------------
def pay_load_num_field():
    # 월임대료, 수도요금 등록 수정 삭제
    
    house_name = request.args.get("house_name", "").strip()
    room_num = request.args.get("room_num", "").strip()
    s_date = request.args.get("s_date", "").strip()
    
    # s_date가 비어있을 경우 기본값(예: 올해 년도) 처리
    if not s_date:
        s_date = str(datetime.now().year)

    print("======================================")
    print("[pay_load_num_field]")
    print("house_name =", repr(house_name))
    print("room_num   =", repr(room_num))
    print("s_date     =", repr(s_date))
    print("======================================")

    conn = get_db()
    cursor = conn.cursor()

    sql = """
        SELECT *
        FROM room_ipkum_tb
        WHERE house_name = ?
          AND room_num = ?
          AND ipkum_day LIKE ?
        ORDER BY ipkum_day ASC
    """

    cursor.execute(sql, (house_name, room_num, f"{s_date}%"))
    rows = cursor.fetchall()
    
    html = ""

    for row in rows:
        html += "<tr>\n"
        html += f"    <td>{row['ipkum_day']}</td>\n"
        html += f"    <td>{row['ipkum_won']}</td>\n"
        html += f"    <td>{row['ipkum_name']}</td>\n"
        html += f"    <td>{row['water_ck']}</td>\n"
        html += f"    <td><a href='#' onclick=\"delete_ipkum('{row['id_num']}')\">X</a></td>\n"
        html += "</tr>\n"

    # 임대료 등록 입력 부분
    html += "<tr>\n"
    html += "    <form name='ipkum_add_form' method='post'>\n"

    html += "       <input type='hidden' name='id_num'>\n"
    html += f"      <input type='hidden' name='house_name' value='{house_name}'>\n"
    html += f"      <input type='hidden' name='room_num' value='{room_num}'>\n"

    html += f"      <td><input class='wid_80px' type='text' name='ipkum_date' value='{TODAY}'></td>\n"

    html += (
        f"      <td><input class='wid_80px' type='text' "
        f"inputmode='numeric' name='ipkum_won' "
        f"value='{_get_room_rent_price(house_name, room_num)}'></td>\n"
    )

    html += (
        f"      <td><input class='wid_100px' type='text' "
        f"name='ipkum_name' "
        f"value='{_get_renter_name(house_name, room_num)}'></td>\n"
    )

    html += (
        "      <td><input class='wid_10px' type='checkbox' "
        "name='water_ck' value='1'></td>\n"
    )

    html += "</tr>\n"

    html += "<tr>\n"
    html += "      <td colspan='5' align='center'>\n"

    html += (
        "        <input type='button' name='btn_ip_kum_add' "
        "value='등록' onclick='ipkum_add_submit();'>"
    )

    html += (
        "        <input type='button' name='btn_cancel' "
        "value='취소' onclick='add_cencel();'>"
    )

    html += "      </td>\n"
    html += "   </form>\n"
    html += "</tr>\n"

    return html


def _date_year(s_date=""):
    selected_year = str(s_date).strip() if s_date else ""

    options = ["<option value='선택'>선택</option>" ]

    for year in DATE_YEAR_ARR:
        year_str = str(year)
        sel = "selected" if selected_year and year_str == selected_year else ""

        options.append(
            f"<option value='{year_str}' {sel}>{year_str}</option>"
        )

    options_html = "".join(options)

    html = (
        "<select name='d_year' class='wid_80px' "
        "onchange=\"year_onchange(this.value)\">"
        f"{options_html}"
        "</select>"
    )

    return html

def _date_month(s_month="") -> str:
    s_month_str = str(s_month) if s_month else ""
    html_out = ["<select name='d_month' class='wid_60px'>"]

    for month in DATE_MONTH_ARR:
        # '01', '02' 형태로 맞춰주기 위해 zfill(2) 사용 (필요시)
        m_str = str(month).zfill(2)
        sel = "selected" if str(month) == str(s_month) or m_str == s_month_str else ""
        html_out.append(f"<option value='{m_str}' {sel}>{month}월</option>")

    html_out.append("</select>")
    return "".join(html_out)

# -------------------------------------------------------------------
# 6. 공통 삭제 처리
# -------------------------------------------------------------------
def _delete(f_type):
    conn = get_db()
    cursor = conn.cursor()

    room_num = _replace(request.values.get("room_num"))
    id_num = request.values.get("id_num") or 0
    pr_name = _replace(request.values.get("pr_name"))

    if f_type == "house_del":
        house_name = _replace(request.values.get("house_name"))
        cursor.execute(
            "DELETE FROM house_tb WHERE m_house_name = ? OR id_num = ?",
            (house_name, id_num),
        )
        conn.commit()

    elif f_type == "room_delete":
        cursor.execute(
            "SELECT house_name FROM room_private_tb WHERE room_num = ? AND pr_name = ?",
            (room_num, pr_name),
        )
        row = cursor.fetchone()
        house_name = row["house_name"] if row else ""

        cursor.execute(
            "DELETE FROM room_private_tb WHERE room_num = ? AND pr_name = ?",
            (room_num, pr_name),
        )
        conn.commit()

        if cursor.rowcount > 0 and house_name:
            _set_room_rent_state(house_name, room_num, "0")

    elif f_type == "house_room_delete":
        cursor.execute(
            "SELECT * FROM p_room_info_tb WHERE id_num = ?", (id_num,)
        )
        row = cursor.fetchone()

        if row:
            p_house_name = row["p_house_name"]
            p_room_num = row["p_room_num"]

            cursor.execute(
                "DELETE FROM p_room_info_tb WHERE id_num = ?", (id_num,)
            )
            cursor.execute(
                "DELETE FROM room_private_tb WHERE house_name = ? AND room_num = ?",
                (p_house_name, p_room_num),
            )
            conn.commit()

    elif f_type == "room_private_delete":
        cursor.execute(
            "DELETE FROM room_private_tb WHERE id_num = ?", (id_num,)
        )
        conn.commit()

    elif f_type == "ipkum_delete":
        cursor.execute("DELETE FROM room_ipkum_tb WHERE id_num = ?", (id_num,))
        conn.commit()

    elif f_type == "outkum_delete":
        cursor.execute("DELETE FROM room_outkum_tb WHERE id_num = ?", (id_num,))
        conn.commit()

    session["msg"] = "삭제되었습니다."
    return redirect(request.referrer or "/")


from flask import render_template, request


# URL 경로를 기존 PHP 경로 형식으로 등록
@app.route("/rent_house_print_form")
@app.route( "/rent_house_print_form.php")  # .php 확장자로 호출해도 동작하도록 함께 등록
def rent_house_print_form():
    # 1. GET 파라미터 수신 (houseName -> tenant_name)
    tenant_name = request.args.get("tenant_name", "")

    conn = get_db()
    cursor = conn.cursor()

    try:
        # 2. 건물 정보 및 해당 건물의 방/입금 내역 조회
        sql_house = "SELECT * FROM house_tb WHERE m_house_name = ?"
        cursor.execute(sql_house, (tenant_name,))
        house_info = cursor.fetchone()

        sql_ipkum = """
            SELECT * FROM room_ipkum_tb 
            WHERE house_name = ? 
            ORDER BY room_num ASC, ipkum_day DESC
        """
        cursor.execute(sql_ipkum, (tenant_name,))
        ipkum_list = cursor.fetchall()

    finally:
        cursor.close()
        conn.close()

    # 3. templates/inc/rent_house_print_form.html 템플릿 반환
    return render_template(
        "/rent_house_print_form.php",
        tenant_name=tenant_name,
        house_info=house_info,
        ipkum_list=ipkum_list,
    )

if __name__ == "__main__":
  # DB 파일이 없을 때만 초기화 실행
  if not os.path.exists("your_database.db"):
    check_and_init_db()
    init_database()

  app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)

   

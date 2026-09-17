import os
import sqlite3
from werkzeug.security import generate_password_hash

# SQLite 데이터베이스 파일명 지정
DB_FILENAME = "rent.db"

# create_db.py
def get_db_connection():
    """SQLite DB 연결 객체 반환"""
    conn = sqlite3.connect(DB_FILENAME)
    conn.row_factory = sqlite3.Row  # 컬럼명으로 접근 가능하도록 설정
    return conn


def create_user_tb(cursor):
    """1. user_tb (사용자/관리자 테이블) 생성 및 초기 관리자 데이터 추가"""
    snb = "user_tb"

    # 기존 테이블 삭제 (DROP)
    cursor.execute(f"DROP TABLE IF EXISTS {snb}")

    # SQLite 호환 테이블 생성
    cursor.execute(
        f"""
        CREATE TABLE {snb} (
            id_num INTEGER PRIMARY KEY AUTOINCREMENT,
            u_id TEXT NOT NULL,
            u_pw TEXT NOT NULL,
            h_manage TEXT NOT NULL,
            u_lebel TEXT NOT NULL
        )
    """
    )
    print(f"{snb} 테이블이 생성되었습니다.")

    # 초기 최고관리자(admin) 데이터 저장
    u_id = "admin"
    h_manage = "필하우스,읍내동 주택"
    u_pw = generate_password_hash("1234")
    u_lebel = "1"

    cursor.execute(
        f"INSERT INTO {snb} (u_id, h_manage, u_pw, u_lebel) VALUES (?, ?, ?, ?)",
        (u_id, h_manage, u_pw, u_lebel),
    )
    print(f"{snb} 테이블에 최고관리자({u_id}) 데이터가 저장되었습니다.")


def create_house_tb(cursor):
    """2. house_tb (원룸/주택 정보 테이블) 생성"""
    snb = "house_tb"

    cursor.execute(f"DROP TABLE IF EXISTS {snb}")
    cursor.execute(
        f"""
        CREATE TABLE {snb} (
            id_num INTEGER PRIMARY KEY AUTOINCREMENT,
            m_house_name TEXT NOT NULL,
            m_address TEXT NOT NULL,
            m_room_all TEXT NOT NULL,
            m_name TEXT NOT NULL,
            m_phone TEXT NOT NULL,
            m_date TEXT NOT NULL
        )
    """
    )
    print(f"{snb} 테이블이 생성되었습니다.")


def create_p_room_info_tb(cursor):
    """3. p_room_info_tb (룸 정보 테이블) 생성"""
    snb = "p_room_info_tb"

    cursor.execute(f"DROP TABLE IF EXISTS {snb}")
    cursor.execute(
        f"""
        CREATE TABLE {snb} (
            id_num INTEGER PRIMARY KEY AUTOINCREMENT,
            p_house_name TEXT NOT NULL,
            p_room_num TEXT NOT NULL,
            p_room_type TEXT NOT NULL,
            p_room_bo TEXT NOT NULL,
            p_room_month_won TEXT NOT NULL,
            p_room_option TEXT NOT NULL,
            p_room_state TEXT NOT NULL,
            p_date TEXT NOT NULL
        )
    """
    )
    print(f"{snb} 테이블이 생성되었습니다.")


def create_room_private_tb(cursor):
    """4. room_private_tb (임차인 정보 테이블) 생성"""
    snb = "room_private_tb"

    cursor.execute(f"DROP TABLE IF EXISTS {snb}")
    cursor.execute(
        f"""
        CREATE TABLE {snb} (
            id_num INTEGER PRIMARY KEY AUTOINCREMENT,
            house_name TEXT NOT NULL,
            room_num TEXT NOT NULL,
            pr_name TEXT NOT NULL,
            pr_number TEXT NOT NULL,
            pr_phone_num TEXT NOT NULL,
            pr_address TEXT NOT NULL,
            pr_email TEXT NOT NULL,
            pr_rent_start TEXT NOT NULL,
            pr_rent_end TEXT NOT NULL
        )
    """
    )
    print(f"{snb} 테이블이 생성되었습니다.")


def create_room_ipkum_tb(cursor):
    """5. room_ipkum_tb (입금 내역 테이블) 생성"""
    snb = "room_ipkum_tb"

    cursor.execute(f"DROP TABLE IF EXISTS {snb}")
    cursor.execute(
        f"""
        CREATE TABLE {snb} (
            id_num INTEGER PRIMARY KEY AUTOINCREMENT,
            house_name TEXT NOT NULL,
            room_num TEXT NOT NULL,
            ipkum_name TEXT NOT NULL,
            ipkum_day TEXT NOT NULL,
            ipkum_won TEXT NOT NULL,
            water_ck TEXT NOT NULL,
            ipkum_gita TEXT NOT NULL
        )
    """
    )
    print(f"{snb} 테이블이 생성되었습니다.")


def create_room_outkum_tb(cursor):
    """6. room_outkum_tb (출금 내역 테이블) 생성"""
    snb = "room_outkum_tb"

    cursor.execute(f"DROP TABLE IF EXISTS {snb}")
    cursor.execute(
        f"""
        CREATE TABLE {snb} (
            id_num INTEGER PRIMARY KEY AUTOINCREMENT,
            house_name TEXT NOT NULL,
            room_num TEXT NOT NULL,
            outkum_name TEXT NOT NULL,
            outkum_day TEXT NOT NULL,
            outkum_won TEXT NOT NULL,
            outkum_gita TEXT NOT NULL
        )
    """
    )
    print(f"{snb} 테이블이 생성되었습니다.")


def init_database():
    """모든 테이블을 순서대로 생성하는 통합 함수"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        print("=== 데이터베이스 초기화를 시작합니다 ===")
        create_user_tb(cursor)
        create_house_tb(cursor)
        create_p_room_info_tb(cursor)
        create_room_private_tb(cursor)
        create_room_ipkum_tb(cursor)
        create_room_outkum_tb(cursor)

        conn.commit()
        print("=== 모든 테이블이 성공적으로 생성 및 초기화되었습니다 ===")
    except Exception as e:
        conn.rollback()
        print(f"데이터베이스 초기화 중 오류 발생: {e}")
    finally:
        conn.close()

def check_and_init_db():
    """DB 파일 및 핵심 테이블 존재 여부를 확인하고, 없을 경우에만 초기화를 진행합니다."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # user_tb 테이블 존재 여부 확인
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='user_tb'"
        )
        table_exists = cursor.fetchone()
    except Exception:
        table_exists = None
    finally:
        conn.close()

    # 테이블이 없거나 DB 조회가 안 되면 전체 초기화 진행
    if not table_exists:
        print("[DB Check] 데이터베이스 테이블이 존재하지 않습니다. 초기 생성을 진행합니다...")
        init_database()
    else:
        print("[DB Check] 데이터베이스가 정상적으로 연결되었습니다.")

if __name__ == "__main__":
    init_database()
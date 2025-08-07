# 서천고 배드민턴 부 운영 웹
import streamlit as st
from datetime import datetime
import pandas as pd
import random
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ------------------ 🔐 구글 시트 인증 ------------------
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = st.secrets["gcp_service_account"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open_by_url(st.secrets["spreadsheet_url"]).sheet1

# ------------------ 🧠 세션 상태 초기화 ------------------
def initialize_session_state():
    defaults = {
        "participants": {},
        "non_attendees": {},
        "attendance": {},
        "game_results": [],
        "is_admin": False,
        "teams": [],
        "team_pairs": {},
        "match_scores": {},
        "password": "",
        "partner_selections": {},
        "score_inputs": {}
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

initialize_session_state()

# ------------------ 🎨 스타일 ------------------
st.set_page_config(page_title="서천고 배드민트 부 운영 웹", layout="wide")
st.markdown("""
    <style>
    .title {text-align: center; color: teal; font-size: 36px; font-weight: bold; margin-bottom: 10px;}
    .subtitle {text-align: center; font-size: 20px; margin-bottom: 30px;}
    .team-box {border: 2px solid #00bcd4; border-radius: 10px; padding: 10px; margin-bottom: 20px; background-color: #f0f9fb;}
    </style>
    <div class="title">🏸 서천고 배드미터 부 운영 웹</div>
    <hr>
""", unsafe_allow_html=True)

# ------------------ 🔐 관리자 로그인 ------------------
with st.sidebar:
    st.markdown("### 🔐 관리자 모드")
    st.session_state.password = st.text_input("비밀번호 입력", type="password", value=st.session_state.password)
    if st.session_state.password == "04281202":
        st.session_state.is_admin = True
        st.success("관리자 모드 활성화됨")
    elif st.session_state.password:
        st.error("비밀번호가 틀립니다")

# ------------------ 👤 비관리자 화면 ------------------
if not st.session_state.is_admin:
    name = st.text_input("👤 성명을 입력하세요")
    going = st.radio("오늘 점심에 오나요?", ['예', '아니오'], horizontal=True)

    if name:
        if going == '예':
            before = st.checkbox("점심시간 전 (1:00~1:10)")
            after = st.checkbox("점심시간 후 (1:30~1:40)")
            if st.button("✅ 제출"):
                st.session_state.participants[name] = {"before": before, "after": after}
                st.success("제출을 완료하였습니다.")

        elif going == '아니오':
            reason = st.text_input("❗ 불참 사유를 작성해주세요.")
            if st.button("🚫 불참 제출"):
                if reason.strip():
                    st.session_state.non_attendees[name] = reason
                    st.success("제출을 완료하였습니다.")
                else:
                    st.warning("사유를 작성해주세요.")

    # 참가자 현황 표시
    if st.session_state.participants:
        st.markdown("### 🧲 참가자 현황")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**🍱 점심 전 참가자**")
            for n, times in st.session_state.participants.items():
                if times.get("before"):
                    st.write(f"- {n}")
        with col2:
            st.markdown("**🍵 점심 후 참가자**")
            for n, times in st.session_state.participants.items():
                if times.get("after"):
                    st.write(f"- {n}")

    # 조 포성 발표
    if st.session_state.teams:
        st.markdown("### 🎽 조 편성 결과")
        for session in ["before", "after"]:
            st.markdown(f"## {'🍱 점심 전' if session == 'before' else '🍵 점심 후'} 조 편성")
            for i in range(1, 4):
                court_index = f"{session}_{i}"
                team = [p for pair in st.session_state.team_pairs.get(court_index, ([], [])) for p in pair]
                st.markdown(f"#### 🎯 {i}코트")
                col1, col2 = st.columns(2)
                with col1:
                    team1 = st.multiselect(f"1팀 선택 ({i}코트)", team, key=f"team1_{court_index}")
                with col2:
                    team2 = st.multiselect(f"2팀 선택 ({i}코트)", team, key=f"team2_{court_index}")
                score = st.text_input("점수 입력 (21-18 형식)", key=f"score_{court_index}")
                if st.button("✅ 결과 저장", key=f"submit_{court_index}"):
                    st.session_state.match_scores[court_index] = {
                        "팀1": team1,
                        "팀2": team2,
                        "점수": score,
                        "시간": datetime.now().strftime("%H:%M:%S")
                    }
                    st.success(f"{i}코트 결과가 저장되었습니다.")

# ------------------ 🛠️ 관리자 기능 ------------------
else:
    st.sidebar.markdown("## 📋 관리자 기능")
    if st.sidebar.button("👥 불참자 확인"):
        st.markdown("### ❌ 불참자 멤버")
        for name, reason in st.session_state.non_attendees.items():
            st.write(f"- {name}: {reason}")

    if st.sidebar.button("🎲 조 편성"):
        team_pairs = {}
        for session in ["before", "after"]:
            players = [n for n, t in st.session_state.participants.items() if t.get(session)]
            random.shuffle(players)
            teams = [players[i:i+4] for i in range(0, min(len(players), 12), 4)]
            for i, team in enumerate(teams, start=1):
                court_index = f"{session}_{i}"
                team1 = team[:2]
                team2 = team[2:] if len(team) >= 4 else []
                if not team2:
                    team2 = [p for p in players if p not in team1]
                team_pairs[court_index] = (team1, team2)
        st.session_state.team_pairs = team_pairs
        st.session_state.teams = list(team_pairs.keys())
        st.success("✅ 점심 전/후 조가 편성되었습니다!")
        st.rerun()

    if st.sidebar.button("🎯 출석 현황 보기"):
        if st.session_state.match_scores:
            st.markdown("### 🕒 출석 현황 (경기 제출 시간 기준)")
            attendance_data = []
            for result in st.session_state.match_scores.values():
                time = result.get("\uc2dc\uac04", "")
                for player in result.get("\ud3001", []) + result.get("\ud3002", []):
                    attendance_data.append({"\uc774\ub984": player, "\uc81c\uc8fc \uc2dc\uac04": time})
            df = pd.DataFrame(attendance_data).drop_duplicates().sort_values("\uc81c\uc8fc \uc2dc\uac04")
            st.dataframe(df, use_container_width=True)
        else:
            st.info("제출된 경기가 없습니다.")

    if st.sidebar.button("🔄 초기화"):
        for key in ["participants", "non_attendees", "attendance", "game_results", "teams", "team_pairs", "match_scores", "partner_selections"]:
            st.session_state[key] = {} if isinstance(st.session_state[key], dict) else []
        st.success("세션이 초기화되었습니다.")

    if st.sidebar.button("🚪 관리자 모드 종료"):
        st.session_state.is_admin = False
        st.session_state.password = ""
        st.rerun()

    if st.sidebar.button("📂 구굴 시트에 저장"):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for name, status in st.session_state.participants.items():
            times = []
            if status["before"]:
                times.append("\uc804")
            if status["after"]:
                times.append("\ud6c4")
            time_str = ", ".join(times) if times else "\ubbf8\ucc38\uc5ec"
            sheet.append_row([now, name, f"\ucc38\uac00 ({time_str})"])
        for name, reason in st.session_state.non_attendees.items():
            sheet.append_row([now, name, "\ubd88\ucc38", reason])
        for i, result in st.session_state.match_scores.items():
            sheet.append_row([now, " & ".join(result["\ud3001"]), " & ".join(result["\ud3002"]), result["\uc810\uc218"], result["\uc2dc\uac04"]])
        st.success("✅ 모든 데이터가 구굴 시트에 저장되었습니다!")

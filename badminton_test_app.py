# 서천고 배드민턴 부 운영 웹
import streamlit as st
from datetime import datetime
import pandas as pd
import random
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ------------------ 🔐 구글 시트 인증 ------------------
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = st.secrets["gcp_service_account"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open_by_url(st.secrets["spreadsheet_url"]).sheet1

# ------------------ 🧠 세션 상태 초기화 ------------------
if "participants" not in st.session_state:
    st.session_state.participants = {}  # 이름별 before/after 정보 저장
if "non_attendees" not in st.session_state:
    st.session_state.non_attendees = {}
if "attendance" not in st.session_state:
    st.session_state.attendance = {}
if "game_results" not in st.session_state:
    st.session_state.game_results = []
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False
if "teams" not in st.session_state:
    st.session_state.teams = []
if "team_pairs" not in st.session_state:
    st.session_state.team_pairs = {}
if "match_scores" not in st.session_state:
    st.session_state.match_scores = {}
if "password" not in st.session_state:
    st.session_state.password = ""

# ------------------ 🎨 스타일 ------------------
st.set_page_config(page_title="서천고 배드민턴 부 운영 웹", layout="wide")
st.markdown("""
    <style>
    .title {text-align: center; color: teal; font-size: 36px; font-weight: bold; margin-bottom: 10px;}
    .subtitle {text-align: center; font-size: 20px; margin-bottom: 30px;}
    </style>
    <div class="title">🏸 서천고 배드민턴 부 운영 웹</div>
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
        st.error("비밀번호가 틀렸습니다")

# ------------------ 👤 비관리자 화면 ------------------
if not st.session_state.is_admin:
    name = st.text_input("👤 성명을 입력하세요")
    if name:
        going = st.radio("오늘 점심에 오나요?", ['예', '아니오'], horizontal=True)

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

    # 참가자 현황
    if st.session_state.participants:
        st.markdown("### 👥 참가자 현황")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**🍱 점심시간 전 참가자**")
            for name, status in st.session_state.participants.items():
                if status["before"]:
                    st.write(name)
        with col2:
            st.markdown("**🍵 점심시간 후 참가자**")
            for name, status in st.session_state.participants.items():
                if status["after"]:
                    st.write(name)

    # 조 편성된 경우 표시
    if st.session_state.teams:
        st.markdown("### 🏸 조 편성 결과")
        for i, team in enumerate(st.session_state.teams, start=1):
            st.markdown(f"#### 🎯 {i}코트")
            team1, team2 = st.session_state.team_pairs.get(i, ([], []))
            col1, col2 = st.columns(2)
            with col1:
                selected_team1 = st.multiselect(f"1팀 선택 ({i}코트)", team, default=team1, key=f"team1_{i}")
            with col2:
                selected_team2 = st.multiselect(f"2팀 선택 ({i}코트)", team, default=team2, key=f"team2_{i}")
            score1 = st.number_input(f"1팀 점수 ({i}코트)", min_value=0, max_value=30, key=f"score1_{i}")
            score2 = st.number_input(f"2팀 점수 ({i}코트)", min_value=0, max_value=30, key=f"score2_{i}")
            if st.button(f"⚔️ 경기 결과 저장 ({i}코트)"):
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                st.session_state.match_scores[i] = {
                    "팀1": selected_team1,
                    "팀2": selected_team2,
                    "점수": f"{score1} : {score2}",
                    "시간": now
                }
                st.success(f"{i}코트 경기 결과가 저장되었습니다.")

# ------------------ 🛠️ 관리자 기능 ------------------
else:
    st.sidebar.markdown("## 📋 관리자 기능")
    if st.sidebar.button("👥 불참자 확인"):
        st.markdown("### ❌ 불참자 명단")
        for name, reason in st.session_state.non_attendees.items():
            st.write(f"- {name}: {reason}")

    if st.sidebar.button("🎲 조 편성"):
        players = list(st.session_state.participants.keys())
        random.shuffle(players)
        teams = [players[i:i+4] for i in range(0, min(len(players), 12), 4)]
        st.session_state.teams = teams
        st.session_state.team_pairs = {}
        st.rerun()

    if st.sidebar.button("🔄 초기화"):
        for key in ["participants", "non_attendees", "attendance", "game_results", "teams", "team_pairs", "match_scores"]:
            st.session_state[key] = {} if isinstance(st.session_state[key], dict) else []
        st.success("세션이 초기화되었습니다.")

    if st.sidebar.button("🚪 관리자 모드 종료"):
        st.session_state.is_admin = False
        st.session_state.password = ""
        st.rerun()

    if st.sidebar.button("💾 구글 시트에 저장"):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for name, status in st.session_state.participants.items():
            times = []
            if status["before"]:
                times.append("전")
            if status["after"]:
                times.append("후")
            time_str = ", ".join(times) if times else "미참여"
            sheet.append_row([now, name, f"참가 ({time_str})"])
        for name, reason in st.session_state.non_attendees.items():
            sheet.append_row([now, name, "불참", reason])
        for i, result in st.session_state.match_scores.items():
            sheet.append_row([now, " & ".join(result["팀1"]), " & ".join(result["팀2"]), result["점수"], result["시간"]])
        st.success("✅ 모든 데이터가 구글 시트에 저장되었습니다!")

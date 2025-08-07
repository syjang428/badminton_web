# 서천고 배드민턴 부 운영 웹

import streamlit as st
from datetime import datetime
import pandas as pd
import random
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# ------------------ 🔐 구글 시트 인증 ------------------
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = st.secrets["gcp_service_account"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

spreadsheet_url = st.secrets["spreadsheet_url"]
spreadsheet = client.open_by_url(spreadsheet_url)

# ------------------ 🧠 세션 상태 초기화 ------------------
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

if "participants" not in st.session_state:
    st.session_state.participants = {}

if "non_attendees" not in st.session_state:
    st.session_state.non_attendees = {}

if "teams" not in st.session_state:
    st.session_state.teams = {}

# ------------------ 🎨 화면 UI 구성 ------------------
st.title("🏸 서천고 배드민턴 부 운영 웹")
st.caption("참가자 확인 → 조 편성 → 경기 결과 입력까지 한 번에!")

# ------------------ 🔑 관리자 모드 전환 ------------------
menu = st.sidebar.selectbox("모드 선택", ["사용자 모드 👤", "관리자 모드 🔐"])
st.session_state.is_admin = True if menu == "관리자 모드 🔐" else False

# ------------------ 👤 비관리자 화면 ------------------
if not st.session_state.is_admin:
    if not st.session_state.teams:  # 조 편성 전까지만 입력 허용
        name = st.text_input("👤 성명을 입력하세요")
        going = st.radio("오늘 점심에 오나요?", ['예', '아니오'], horizontal=True)

        if going == '예':
            before = st.checkbox("점심시간 전 (1:00~1:10)", key="before_check")
            after = st.checkbox("점심시간 후 (1:30~1:40)", key="after_check")
            if st.button("✅ 제출"):
                if name.strip():
                    st.session_state.participants[name] = {"before": before, "after": after}
                    st.success("제출을 완료하였습니다.")
                else:
                    st.warning("이름을 입력해주세요.")

        elif going == '아니오':
            reason = st.text_input("❗ 불참 사유를 작성해주세요.")
            if st.button("🚫 불참 제출"):
                if name.strip() and reason.strip():
                    st.session_state.non_attendees[name] = reason
                    st.success("제출을 완료하였습니다.")
                elif not name.strip():
                    st.warning("이름을 입력해주세요.")
                else:
                    st.warning("불참 사유를 작성해주세요.")

        # ✅ 참가자 현황 표시 (조 편성 전까지만)
        st.markdown("### 🧲 참가자 현황")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**🍱 점심 전 참가자**")
            before_players = [n for n, t in st.session_state.participants.items() if t.get("before")]
            if before_players:
                for n in before_players:
                    st.write(f"- {n}")
            else:
                st.write("없음")

        with col2:
            st.markdown("**🍵 점심 후 참가자**")
            after_players = [n for n, t in st.session_state.participants.items() if t.get("after")]
            if after_players:
                for n in after_players:
                    st.write(f"- {n}")
            else:
                st.write("없음")

# ------------------ 🛠️ 관리자 화면 ------------------
if st.session_state.is_admin:
    st.subheader("🛠️ 관리자 기능")

    # 참가자 현황 출력
    st.markdown("### 🧲 참가자 현황")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**🍱 점심 전 참가자**")
        before_players = [n for n, t in st.session_state.participants.items() if t.get("before")]
        if before_players:
            for n in before_players:
                st.write(f"- {n}")
        else:
            st.write("없음")

    with col2:
        st.markdown("**🍵 점심 후 참가자**")
        after_players = [n for n, t in st.session_state.participants.items() if t.get("after")]
        if after_players:
            for n in after_players:
                st.write(f"- {n}")
        else:
            st.write("없음")

    # 팀 수동 선택용 placeholder
    st.markdown("### 🧩 조 편성")
    session = st.radio("세션을 선택하세요", ["점심 전", "점심 후"])
    session_key = "before" if session == "점심 전" else "after"

    selected_players = [n for n, t in st.session_state.participants.items() if t.get(session_key)]

    if len(selected_players) < 4:
        st.info("조 편성을 위해 최소 4명의 참가자가 필요합니다.")
    else:
        num_courts = 3  # 코트 수
        max_players = num_courts * 4
        trimmed_players = selected_players[:max_players]
        random.shuffle(trimmed_players)

        teams = []
        for i in range(0, len(trimmed_players), 4):
            group = trimmed_players[i:i+4]
            if len(group) == 4:
                team1 = st.multiselect(f"{group} → 팀 1 선택 (2명)", group, key=f"{group}_team1", max_selections=2)
                team2 = [p for p in group if p not in team1] if len(team1) == 2 else []
                if len(team1) == 2 and len(team2) == 2:
                    teams.append((team1, team2))

        if st.button("🚀 조 편성 완료"):
            if all(len(team1) == 2 and len(team2) == 2 for team1, team2 in teams):
                st.session_state.teams[session_key] = teams
                st.success("조 편성이 완료되었습니다.")
            else:
                st.error("모든 그룹에서 팀 1과 팀 2를 정확히 2명씩 선택해야 합니다.")

# ------------------ 📋 조 편성 결과 출력 ------------------
if st.session_state.teams:
    st.markdown("## 📋 조 편성 결과")

    for session_key, teams in st.session_state.teams.items():
        session_name = "점심 전" if session_key == "before" else "점심 후"
        st.markdown(f"### ⏰ {session_name}")
        for idx, (team1, team2) in enumerate(teams):
            st.markdown(f"#### 코트 {idx + 1}")
            st.write(f"🅰️ {' · '.join(team1)}")
            st.write(f"🅱️ {' · '.join(team2)}")

# ------------------ 🔄 조 편성 초기화 ------------------
if st.session_state.is_admin and st.session_state.teams:
    if st.button("🔄 조 편성 초기화"):
        st.session_state.teams = {}
        st.success("조 편성이 초기화되었습니다.")

# ------------------ 🏆 경기 결과 입력 ------------------
if st.session_state.is_admin and st.session_state.teams:
    st.markdown("## 🏆 경기 결과 입력")

    if "match_results" not in st.session_state:
        st.session_state.match_results = {}

    for session_key, teams in st.session_state.teams.items():
        session_name = "점심 전" if session_key == "before" else "점심 후"
        st.markdown(f"### ⏰ {session_name}")
        for idx, (team1, team2) in enumerate(teams):
            st.markdown(f"#### 코트 {idx + 1}")
            col1, col2 = st.columns(2)
            with col1:
                score1 = st.number_input(f"🅰️ {' · '.join(team1)} 점수", min_value=0, key=f"{session_key}_{idx}_1")
            with col2:
                score2 = st.number_input(f"🅱️ {' · '.join(team2)} 점수", min_value=0, key=f"{session_key}_{idx}_2")

            st.session_state.match_results[f"{session_key}_{idx}"] = {
                "court": idx + 1,
                "session": session_name,
                "team1": team1,
                "team2": team2,
                "score1": score1,
                "score2": score2,
            }

# ------------------ 📤 Google Sheets 저장 ------------------
if st.session_state.is_admin:
    if st.button("📤 Google Sheets에 저장"):
        # 📄 시트 준비
        try:
            participant_sheet = spreadsheet.worksheet("참가자")
        except:
            participant_sheet = spreadsheet.add_worksheet(title="참가자", rows="100", cols="10")
        participant_sheet.clear()

        non_attendee_sheet = None
        try:
            non_attendee_sheet = spreadsheet.worksheet("불참자")
        except:
            non_attendee_sheet = spreadsheet.add_worksheet(title="불참자", rows="100", cols="10")
        non_attendee_sheet.clear()

        team_sheet = None
        try:
            team_sheet = spreadsheet.worksheet("조편성")
        except:
            team_sheet = spreadsheet.add_worksheet(title="조편성", rows="100", cols="10")
        team_sheet.clear()

        result_sheet = None
        try:
            result_sheet = spreadsheet.worksheet("경기결과")
        except:
            result_sheet = spreadsheet.add_worksheet(title="경기결과", rows="100", cols="10")
        result_sheet.clear()

        # ✅ 참가자 저장
        p_data = [["이름", "점심 전", "점심 후"]]
        for name, times in st.session_state.participants.items():
            p_data.append([name, "O" if times["before"] else "", "O" if times["after"] else ""])
        participant_sheet.update("A1", p_data)

        # ❌ 불참자 저장
        n_data = [["이름", "사유"]]
        for name, reason in st.session_state.non_attendees.items():
            n_data.append([name, reason])
        non_attendee_sheet.update("A1", n_data)

        # 🧩 조 편성 저장
        t_data = [["세션", "코트", "팀 A", "팀 B"]]
        for session_key, teams in st.session_state.teams.items():
            session_name = "점심 전" if session_key == "before" else "점심 후"
            for idx, (team1, team2) in enumerate(teams):
                t_data.append([session_name, idx + 1, ", ".join(team1), ", ".join(team2)])
        team_sheet.update("A1", t_data)

        # 🏆 경기 결과 저장
        r_data = [["세션", "코트", "팀 A", "점수 A", "팀 B", "점수 B"]]
        for key, match in st.session_state.match_results.items():
            r_data.append([
                match["session"],
                match["court"],
                ", ".join(match["team1"]),
                match["score1"],
                ", ".join(match["team2"]),
                match["score2"]
            ])
        result_sheet.update("A1", r_data)

        st.success("✅ 모든 데이터가 Google Sheets에 저장되었습니다.")

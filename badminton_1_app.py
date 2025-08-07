# ------------------ 서천고 배드민턴 부 운영 웹 ------------------
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

# ✅ 함수 정의 먼저
def load_data_from_sheet():
    try:
        records = sheet.get_all_records()
        for record in records:
            name = record.get("이름", "").strip()
            status = record.get("상태", "")
            reason = record.get("불참 사유", "")
            team1 = record.get("팀1", "")
            team2 = record.get("팀2", "")
            score = record.get("점수", "")
            time = record.get("시간", "")

            if "참가" in status and name:
                st.session_state.participants[name] = {
                    "before": "전" in status,
                    "after": "후" in status
                }
            elif "불참" in status and name:
                st.session_state.non_attendees[name] = reason
            elif team1 and team2 and score:
                court_key = name  # 이 부분은 경기 저장 방식에 따라 조정 필요
                st.session_state.match_scores[court_key] = {
                    "팀1": team1.split(" & "),
                    "팀2": team2.split(" & "),
                    "점수": score,
                    "시간": time
                }
    except Exception as e:
        st.warning(f"구글 시트 데이터 불러오기 실패: {e}")

# ✅ 그 다음에 조건부 호출
if not st.session_state.get("participants") and not st.session_state.get("non_attendees") and not st.session_state.get("match_scores"):
    load_data_from_sheet()

# ------------------ 🎨 스타일 ------------------
st.set_page_config(page_title="서천고 배드민턴 부 운영 웹", layout="wide")
st.markdown("""
    <style>
    .title {text-align: center; color: teal; font-size: 36px; font-weight: bold; margin-bottom: 10px;}
    .subtitle {text-align: center; font-size: 20px; margin-bottom: 30px;}
    .team-box {border: 2px solid #00bcd4; border-radius: 10px; padding: 10px; margin-bottom: 20px; background-color: #f0f9fb;}
    .waiting {font-size: 14px; color: gray;}
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
        st.error("비밀번호가 틀립니다")

# ------------------ 👤 비관리자 화면 ------------------
if not st.session_state.is_admin:
    if not st.session_state.teams:
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

    if st.session_state.teams:
        st.markdown("### 🎽 조 편성 결과")

        for session in ["before", "after"]:
            players = [n for n, t in st.session_state.participants.items() if t.get(session)]
            paired_players = []

            st.markdown(f"## {'🍱 점심 전' if session == 'before' else '🍵 점심 후'} 조 편성")

            for i in range(1, 4):
                court_index = f"{session}_{i}"
                if court_index in st.session_state.team_pairs:
                    team1, team2 = st.session_state.team_pairs[court_index]
                    total_players = team1 + team2
                    if len(total_players) == 4:
                        paired_players.extend(total_players)
                        st.markdown(f"#### 🎯 {i}코트")
                        col1, col2 = st.columns(2)
                        with col1:
                            team1_sel = st.multiselect(f"1팀 선택 ({i}코트)", total_players, default=team1, key=f"team1_{court_index}")
                        with col2:
                            team2_sel = st.multiselect(f"2팀 선택 ({i}코트)", total_players, default=team2, key=f"team2_{court_index}")
                        score_col1, score_col2 = st.columns(2)
                        with score_col1:
                            score_team1 = st.number_input("1팀 점수", min_value=0, max_value=30, key=f"score1_{court_index}")
                        with score_col2:
                            score_team2 = st.number_input("2팀 점수", min_value=0, max_value=30, key=f"score2_{court_index}")

                        if st.button("✅ 결과 저장", key=f"submit_{court_index}"):
                            score_str = f"{score_team1}-{score_team2}"
                            st.session_state.match_scores[court_index] = {
                                "팀1": team1_sel,
                                "팀2": team2_sel,
                                "점수": score_str,
                                "시간": datetime.now().strftime("%H:%M:%S")
                            }
                            st.success(f"{i}코트 결과가 저장되었습니다.")

            waiting_players = [p for p in players if p not in paired_players]
            if waiting_players:
                st.markdown("<div class='waiting'>⏳ 대기 인원: " + ", ".join(waiting_players) + "</div>", unsafe_allow_html=True)

# ------------------ 🛠️ 관리자 기능 ------------------
else:
    st.sidebar.markdown("## 📋 관리자 기능")
    if st.sidebar.button("👥 불참자 확인"):
        if st.session_state.non_attendees:
            st.markdown("### 🚫 불참자 목록")
            df_non_attendees = pd.DataFrame([
                {"이름": name, "불참 사유": reason}
                for name, reason in st.session_state.non_attendees.items()
            ])
            st.dataframe(df_non_attendees, use_container_width=True)

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
                time = result.get("시간", "")
                for player in result.get("팀1", []) + result.get("팀2", []):
                    attendance_data.append({"이름": player, "제출 시간": time})
            df = pd.DataFrame(attendance_data).drop_duplicates().sort_values("제출 시간")
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

    if st.sidebar.button("📂 구글 시트에 저장"):
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

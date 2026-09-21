# ============================================
# 날짜를 선택해서 보는 박스오피스 - Streamlit 앱
# ============================================
#
# 초보자용 설명:
# 1. 달력에서 조회할 날짜를 선택합니다.
# 2. 오늘 날짜는 아직 집계가 끝나지 않았으므로 선택할 수 없습니다.
# 3. 한국 시간 기준으로 어제까지 선택할 수 있습니다.
# 4. 선택한 날짜의 KOBIS 일일 박스오피스를 가져옵니다.
# 5. 순위가 전날보다 오른 영화에는 빨간색 위 화살표를,
#    내려간 영화에는 파란색 아래 화살표를 표시합니다.
# 6. 누적 관객이 100만 명을 넘은 영화에는 🏆를 붙입니다.
# 7. 같은 날짜를 다시 조회하면 약 1시간 동안 저장된 결과를 사용합니다.
#
# Streamlit Cloud Secrets:
#
# KOBIS_KEY = "본인의_KOBIS_인증키"
#
# ※ 인증키를 이 파일에 직접 넣지 마세요.
# ============================================

import streamlit as st
import requests
import pandas as pd

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


# --------------------------------------------
# 페이지 설정
# --------------------------------------------

st.set_page_config(
    page_title="박스오피스 조회",
    page_icon="🎬",
    layout="wide"
)


# --------------------------------------------
# KOBIS API 주소
# --------------------------------------------

API_URL = (
    "https://www.kobis.or.kr/"
    "kobisopenapi/webservice/rest/boxoffice/"
    "searchDailyBoxOfficeList.json"
)


# --------------------------------------------
# 한국 시간 기준 오늘 날짜 구하기
# --------------------------------------------

def get_korea_today():
    """
    배포 서버가 한국 시간이 아닐 수 있으므로
    반드시 Asia/Seoul 시간대를 사용합니다.
    """

    korea_now = datetime.now(
        ZoneInfo("Asia/Seoul")
    )

    return korea_now.date()


# --------------------------------------------
# 날짜를 KOBIS API용 문자열로 변환
# --------------------------------------------

def date_to_string(date_value):
    """
    날짜를 KOBIS가 요구하는
    yyyymmdd 형식으로 바꿉니다.

    예:
    2026-09-20
    →
    20260920
    """

    return date_value.strftime("%Y%m%d")


# --------------------------------------------
# 숫자 문자열을 숫자로 변환
# --------------------------------------------

def to_number(value):
    """
    KOBIS API의 숫자 값은 문자열로 전달됩니다.

    예:
    "12345" → 12345
    """

    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


# --------------------------------------------
# KOBIS API 호출
# --------------------------------------------

@st.cache_data(ttl=3600)
def get_box_office(target_date):
    """
    선택한 날짜의 박스오피스 자료를 가져옵니다.

    ttl=3600
    → 같은 날짜의 결과를 약 1시간 동안 기억합니다.
    → 따라서 같은 날짜를 다시 선택해도
       API를 계속 호출하지 않습니다.
    """

    # ----------------------------------------
    # Secrets에서 인증키 가져오기
    # ----------------------------------------

    try:
        api_key = st.secrets["KOBIS_KEY"]

    except Exception:
        return {
            "success": False,
            "empty": False,
            "message": (
                "KOBIS_KEY를 찾을 수 없습니다.\n\n"
                "Streamlit Cloud의 앱 설정에서 "
                "Secrets에 KOBIS_KEY를 등록했는지 확인하세요."
            ),
            "data": None,
        }

    # ----------------------------------------
    # API 요청값
    # ----------------------------------------

    params = {
        "key": api_key,
        "targetDt": target_date,
    }

    # ----------------------------------------
    # API 요청
    # ----------------------------------------

    try:
        response = requests.get(
            API_URL,
            params=params,
            timeout=15
        )

        response.raise_for_status()

        result = response.json()

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "empty": False,
            "message": (
                "KOBIS API 요청 시간이 초과되었습니다.\n\n"
                "잠시 후 다시 실행해 보세요."
            ),
            "data": None,
        }

    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "empty": False,
            "message": (
                "KOBIS API 요청에 실패했습니다.\n\n"
                f"오류 내용: {e}\n\n"
                "인터넷 연결과 KOBIS API 서버 상태를 "
                "확인해 주세요."
            ),
            "data": None,
        }

    except ValueError:
        return {
            "success": False,
            "empty": False,
            "message": (
                "KOBIS API에서 정상적인 JSON 응답을 "
                "받지 못했습니다.\n\n"
                "잠시 후 다시 실행해 보세요."
            ),
            "data": None,
        }

    # ----------------------------------------
    # faultInfo 확인
    # ----------------------------------------
    #
    # KOBIS는 인증키가 잘못되어도 HTTP 상태코드가
    # 200으로 올 수 있습니다.
    # 따라서 faultInfo를 따로 확인합니다.
    # ----------------------------------------

    if "faultInfo" in result:

        fault_info = result.get(
            "faultInfo",
            {}
        )

        fault_code = fault_info.get(
            "errorCode",
            "알 수 없음"
        )

        fault_message = fault_info.get(
            "errorMessage",
            "알 수 없는 오류입니다."
        )

        return {
            "success": False,
            "empty": False,
            "message": (
                "KOBIS API에서 오류를 반환했습니다.\n\n"
                f"오류 코드: {fault_code}\n"
                f"오류 내용: {fault_message}\n\n"
                "확인할 사항:\n"
                "• Streamlit Secrets의 KOBIS_KEY가 정확한지 확인\n"
                "• 인증키 앞뒤에 불필요한 공백이 없는지 확인\n"
                "• KOBIS API 사용이 가능한 인증키인지 확인"
            ),
            "data": None,
        }

    # ----------------------------------------
    # boxOfficeResult 확인
    # ----------------------------------------

    box_office_result = result.get(
        "boxOfficeResult"
    )

    if not box_office_result:
        return {
            "success": False,
            "empty": False,
            "message": (
                "KOBIS 응답에 boxOfficeResult가 없습니다.\n\n"
                "KOBIS API 서버 상태나 응답 형식을 확인해 주세요."
            ),
            "data": None,
        }

    # ----------------------------------------
    # 영화 목록 가져오기
    # ----------------------------------------

    movie_list = box_office_result.get(
        "dailyBoxOfficeList",
        []
    )

    # ----------------------------------------
    # 영화 목록이 없는 경우
    # ----------------------------------------
    #
    # 요청사항:
    # 영화 목록이 비어 있으면
    # "그날은 아직 집계 전입니다"라고 안내합니다.
    # ----------------------------------------

    if not movie_list:
        return {
            "success": False,
            "empty": True,
            "message": "그날은 아직 집계 전입니다.",
            "data": None,
        }

    # ----------------------------------------
    # 영화 데이터를 표 형태로 변환
    # ----------------------------------------

    rows = []

    for movie in movie_list:

        # 전날 대비 순위 증감
        rank_inten = to_number(
            movie.get("rankInten")
        )

        # 순위 변동 표시 만들기
        if rank_inten > 0:
            rank_change = f"↑ {rank_inten}"

        elif rank_inten < 0:
            rank_change = f"↓ {abs(rank_inten)}"

        else:
            rank_change = "-"

        # 누적 관객수
        audi_acc = to_number(
            movie.get("audiAcc")
        )

        # 누적 관객 100만 명 초과 여부
        if audi_acc > 1_000_000:
            movie_name = (
                f"🏆 {movie.get('movieNm', '')}"
            )
        else:
            movie_name = movie.get(
                "movieNm",
                ""
            )

        rows.append({
            "순위": to_number(
                movie.get("rank")
            ),
            "순위변동값": rank_inten,
            "순위변동": rank_change,
            "영화명": movie_name,
            "개봉일": movie.get(
                "openDt",
                ""
            ),
            "관객수": to_number(
                movie.get("audiCnt")
            ),
            "누적관객": audi_acc,
            "스크린수": to_number(
                movie.get("scrnCnt")
            ),
        })

    # ----------------------------------------
    # DataFrame으로 변환
    # ----------------------------------------

    df = pd.DataFrame(rows)

    # 순위를 숫자 기준으로 정렬
    df = df.sort_values(
        by="순위",
        ascending=True
    ).reset_index(drop=True)

    return {
        "success": True,
        "empty": False,
        "message": "",
        "data": df,
    }


# ============================================
# 화면
# ============================================

st.title("🎬 박스오피스 조회")

st.write(
    "날짜를 선택하면 해당 날짜의 KOBIS 일일 박스오피스를 "
    "확인할 수 있습니다."
)


# --------------------------------------------
# 조회 가능한 날짜 범위 계산
# --------------------------------------------

today_kst = get_korea_today()

# 오늘은 아직 집계 전이므로 어제까지만 선택 가능
latest_date = today_kst - timedelta(days=1)

# 시작 날짜
# 달력에서 너무 먼 과거까지 선택할 수 있도록
# 2000년부터 선택 가능하게 설정했습니다.
first_date = datetime(
    2000,
    1,
    1
).date()


# --------------------------------------------
# 날짜 선택
# --------------------------------------------

selected_date = st.date_input(
    "📅 조회할 날짜를 선택하세요",
    value=latest_date,
    min_value=first_date,
    max_value=latest_date,
)


# --------------------------------------------
# 선택한 날짜 표시
# --------------------------------------------

selected_date_text = selected_date.strftime(
    "%Y년 %m월 %d일"
)

st.info(
    f"📅 선택한 날짜: **{selected_date_text}**"
)


# --------------------------------------------
# KOBIS API용 날짜
# --------------------------------------------

target_date = date_to_string(
    selected_date
)


# --------------------------------------------
# API 호출
# --------------------------------------------

result = get_box_office(
    target_date
)


# --------------------------------------------
# API 오류 처리
# --------------------------------------------

if not result["success"]:

    # 영화 목록이 없는 경우
    if result["empty"]:

        st.warning(
            "📭 그날은 아직 집계 전입니다."
        )

        st.write(
            "다른 날짜를 선택해 보세요."
        )

    # API 자체에 오류가 있는 경우
    else:

        st.error(
            "박스오피스 자료를 가져오지 못했습니다."
        )

        st.warning(
            result["message"]
        )

    # 오류가 있을 때 아래 화면은 표시하지 않음
    st.stop()


# --------------------------------------------
# 정상적으로 데이터를 받은 경우
# --------------------------------------------

df = result["data"]


# ============================================
# 1위 영화
# ============================================

first_movie = df.iloc[0]

st.subheader("🏆 1위 영화")


# --------------------------------------------
# 1위 영화의 지표 카드 세 장
# --------------------------------------------

col1, col2, col3 = st.columns(3)


with col1:
    st.metric(
        label="영화",
        value=first_movie["영화명"]
    )


with col2:
    st.metric(
        label="관객수",
        value=f"{first_movie['관객수']:,}명"
    )


with col3:
    st.metric(
        label="누적관객",
        value=f"{first_movie['누적관객']:,}명"
    )


# --------------------------------------------
# 1위 영화 추가 정보
# --------------------------------------------

st.caption(
    f"개봉일: "
    f"{first_movie['개봉일'] or '정보 없음'}"
    f"  ·  "
    f"스크린수: "
    f"{first_movie['스크린수']:,}개"
)


# ============================================
# 관객수 상위 5편
# ============================================

st.subheader("📊 관객수 상위 5편")


# 관객수가 많은 순서대로 5편 선택
top5 = (
    df.sort_values(
        by="관객수",
        ascending=False
    )
    .head(5)
    .copy()
)


# 그래프용 데이터
chart_data = top5.set_index(
    "영화명"
)[["관객수"]]


# 막대그래프
st.bar_chart(
    chart_data
)


# ============================================
# 전체 박스오피스 표
# ============================================

st.subheader("🎞️ 전체 박스오피스")


# --------------------------------------------
# 화면에 표시할 컬럼
# --------------------------------------------

display_df = df[
    [
        "순위",
        "순위변동",
        "영화명",
        "개봉일",
        "관객수",
        "누적관객",
        "스크린수",
    ]
].copy()


# --------------------------------------------
# 숫자를 보기 쉽게 표시
# --------------------------------------------
#
# 중요:
# 여기서는 화면 표시용 DataFrame만 문자열로 바꿉니다.
#
# 원본 df의 관객수, 누적관객, 스크린수는
# 실제 숫자로 남아 있으므로
# 정렬과 그래프에는 숫자가 사용됩니다.
# --------------------------------------------

display_df["관객수"] = display_df[
    "관객수"
].map(
    lambda x: f"{x:,}"
)


display_df["누적관객"] = display_df[
    "누적관객"
].map(
    lambda x: f"{x:,}"
)


display_df["스크린수"] = display_df[
    "스크린수"
].map(
    lambda x: f"{x:,}"
)


# --------------------------------------------
# 표 표시
# --------------------------------------------

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "순위": st.column_config.NumberColumn(
            "순위"
        ),

        "순위변동": st.column_config.TextColumn(
            "전날 대비"
        ),

        "영화명": st.column_config.TextColumn(
            "영화명"
        ),

        "개봉일": st.column_config.TextColumn(
            "개봉일"
        ),

        "관객수": st.column_config.TextColumn(
            "관객수"
        ),

        "누적관객": st.column_config.TextColumn(
            "누적관객"
        ),

        "스크린수": st.column_config.TextColumn(
            "스크린수"
        ),
    }
)


# --------------------------------------------
# 화살표 설명
# --------------------------------------------

st.caption(
    "🔴 ↑ 순위 상승  ·  🔵 ↓ 순위 하락  ·  "
    "🏆 누적관객 100만 명 초과"
)

st.caption(
    "💡 같은 날짜의 KOBIS 조회 결과는 약 1시간 동안 캐시됩니다."
)

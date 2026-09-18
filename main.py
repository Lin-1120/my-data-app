# ============================================
# 어제의 박스오피스 - Streamlit 앱
# ============================================
# 초보자용 설명:
# 1. 한국 시간 기준으로 "어제" 날짜를 자동으로 계산합니다.
# 2. KOBIS API에 어제 날짜를 보내 박스오피스 자료를 가져옵니다.
# 3. 숫자로 전달되는 값이 문자열이므로 숫자로 변환합니다.
# 4. 결과를 표, 1위 영화 지표 카드, 상위 5편 막대그래프로 보여줍니다.
# 5. API 결과는 약 1시간 동안 캐시해서 같은 날짜에 API를 계속 호출하지 않습니다.
#
# Streamlit Cloud에 올릴 때:
# Secrets에 다음과 같이 KOBIS_KEY를 등록하세요.
#
# KOBIS_KEY = "발급받은_인증키"
#
# ※ 인증키를 이 파일에 직접 적으면 안 됩니다.
# ============================================

import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


# --------------------------------------------
# 기본 페이지 설정
# --------------------------------------------
st.set_page_config(
    page_title="어제의 박스오피스",
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
# 한국 시간 기준으로 어제 날짜 계산
# --------------------------------------------
def get_yesterday_kst():
    """
    배포 서버의 시간이 한국 시간이 아닐 수 있으므로
    반드시 Asia/Seoul 시간대를 사용해서 어제를 계산합니다.

    반환 예:
    20260917
    """
    korea_now = datetime.now(ZoneInfo("Asia/Seoul"))
    yesterday = korea_now.date() - timedelta(days=1)

    return yesterday.strftime("%Y%m%d")


# --------------------------------------------
# 숫자 문자열을 안전하게 숫자로 변환
# --------------------------------------------
def to_number(value):
    """
    KOBIS API의 숫자 값은 문자열로 들어옵니다.

    예:
    "12345" -> 12345

    값이 없거나 변환할 수 없으면 0을 반환합니다.
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
    target_date에 해당하는 일일 박스오피스 자료를 가져옵니다.

    ttl=3600:
    같은 날짜의 API 결과를 약 1시간 동안 캐시합니다.
    따라서 사용자가 새로고침해도 계속 API를 호출하지 않습니다.
    """

    # Streamlit Secrets에서 인증키를 가져옵니다.
    # 코드에 인증키를 직접 적지 않습니다.
    try:
        api_key = st.secrets["KOBIS_KEY"]
    except Exception:
        return {
            "success": False,
            "message": (
                "KOBIS_KEY를 찾을 수 없습니다.\n\n"
                "Streamlit Cloud의 앱 설정에서 "
                "Secrets에 KOBIS_KEY를 등록했는지 확인하세요."
            ),
            "data": None,
        }

    # API 요청에 사용할 값
    params = {
        "key": api_key,
        "targetDt": target_date,
    }

    try:
        # KOBIS API에 요청
        response = requests.get(
            API_URL,
            params=params,
            timeout=15
        )

        # HTTP 자체가 실패한 경우
        response.raise_for_status()

        # JSON으로 변환
        result = response.json()

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "message": (
                "KOBIS API 요청 시간이 초과되었습니다.\n\n"
                "잠시 후 다시 실행해 보세요. "
                "KOBIS 서버 상태나 인터넷 연결도 확인해 주세요."
            ),
            "data": None,
        }

    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "message": (
                "KOBIS API 요청에 실패했습니다.\n\n"
                f"오류 내용: {e}\n\n"
                "인터넷 연결과 KOBIS API 서버 상태를 확인해 주세요."
            ),
            "data": None,
        }

    except ValueError:
        return {
            "success": False,
            "message": (
                "KOBIS API에서 정상적인 JSON 응답을 받지 못했습니다.\n\n"
                "잠시 후 다시 실행해 보세요."
            ),
            "data": None,
        }

    # ----------------------------------------
    # 인증키 오류 등 faultInfo 확인
    # ----------------------------------------
    # KOBIS는 인증키가 잘못되어도 HTTP 상태코드가 200일 수 있고,
    # 이 경우 faultInfo가 들어올 수 있습니다.
    if "faultInfo" in result:
        fault_info = result.get("faultInfo", {})

        fault_code = fault_info.get("errorCode", "알 수 없음")
        fault_message = fault_info.get(
            "errorMessage",
            "알 수 없는 오류입니다."
        )

        return {
            "success": False,
            "message": (
                "KOBIS API에서 오류를 반환했습니다.\n\n"
                f"오류 코드: {fault_code}\n"
                f"오류 내용: {fault_message}\n\n"
                "확인할 사항:\n"
                "• Streamlit Secrets의 KOBIS_KEY가 정확한지 확인\n"
                "• 인증키 앞뒤에 불필요한 공백이 없는지 확인\n"
                "• KOBIS API 사용이 정상적으로 가능한 키인지 확인"
            ),
            "data": None,
        }

    # ----------------------------------------
    # boxOfficeResult 확인
    # ----------------------------------------
    box_office_result = result.get("boxOfficeResult")

    if not box_office_result:
        return {
            "success": False,
            "message": (
                "KOBIS 응답에 boxOfficeResult가 없습니다.\n\n"
                "API 응답 형식이나 KOBIS 서버 상태를 확인해 주세요."
            ),
            "data": None,
        }

    # 영화 목록 가져오기
    movie_list = box_office_result.get(
        "dailyBoxOfficeList",
        []
    )

    # ----------------------------------------
    # 영화 목록이 비어 있는 경우
    # ----------------------------------------
    if not movie_list:
        return {
            "success": False,
            "message": (
                "해당 날짜의 박스오피스 영화 목록이 없습니다.\n\n"
                "확인할 사항:\n"
                "• 조회 날짜가 정상적인 날짜인지 확인\n"
                "• KOBIS에서 해당 날짜의 박스오피스 자료가 집계되었는지 확인\n"
                "• 잠시 후 다시 실행해 보세요."
            ),
            "data": None,
        }

    # ----------------------------------------
    # API에서 받은 자료를 DataFrame으로 변환
    # ----------------------------------------
    rows = []

    for movie in movie_list:
        rows.append({
            "순위": to_number(movie.get("rank")),
            "영화명": movie.get("movieNm", ""),
            "개봉일": movie.get("openDt", ""),
            "관객수": to_number(movie.get("audiCnt")),
            "누적관객": to_number(movie.get("audiAcc")),
            "스크린수": to_number(movie.get("scrnCnt")),
        })

    df = pd.DataFrame(rows)

    # 순위를 숫자 기준으로 정렬
    df = df.sort_values(
        by="순위",
        ascending=True
    ).reset_index(drop=True)

    return {
        "success": True,
        "message": "",
        "data": df,
    }


# --------------------------------------------
# 제목
# --------------------------------------------
st.title("🎬 어제의 박스오피스")

st.write(
    "한국 시간 기준으로 어제 집계된 영화관 박스오피스를 보여줍니다."
)


# --------------------------------------------
# 조회 날짜 표시
# --------------------------------------------
target_date = get_yesterday_kst()

# 사람이 보기 편한 날짜로 변환
display_date = (
    f"{target_date[:4]}년 "
    f"{target_date[4:6]}월 "
    f"{target_date[6:8]}일"
)

st.info(f"📅 조회 날짜: **{display_date}**")


# --------------------------------------------
# API 호출
# --------------------------------------------
result = get_box_office(target_date)


# --------------------------------------------
# API 오류가 발생한 경우
# --------------------------------------------
if not result["success"]:
    st.error("박스오피스 자료를 가져오지 못했습니다.")

    # 사용자가 무엇을 확인해야 하는지 보여줍니다.
    st.warning(result["message"])

    # 오류가 있을 때 아래 내용을 그리지 않고 종료합니다.
    st.stop()


# --------------------------------------------
# 정상적으로 자료를 받은 경우
# --------------------------------------------
df = result["data"]


# --------------------------------------------
# 1위 영화 정보
# --------------------------------------------
first_movie = df.iloc[0]

st.subheader("🏆 오늘의 1위 영화")


# 세 개의 지표 카드를 나란히 표시
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label="영화",
        value=first_movie["영화명"]
    )

with col2:
    st.metric(
        label="어제 관객수",
        value=f"{first_movie['관객수']:,}명"
    )

with col3:
    st.metric(
        label="누적 관객",
        value=f"{first_movie['누적관객']:,}명"
    )


# --------------------------------------------
# 영화 1위의 추가 정보
# --------------------------------------------
st.caption(
    f"개봉일: {first_movie['개봉일'] or '정보 없음'} · "
    f"스크린수: {first_movie['스크린수']:,}개"
)


# --------------------------------------------
# 관객수 상위 5편 막대그래프
# --------------------------------------------
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

# 그래프의 영화명과 관객수만 사용
chart_data = top5.set_index("영화명")[["관객수"]]

st.bar_chart(chart_data)


# --------------------------------------------
# 전체 박스오피스 표
# --------------------------------------------
st.subheader("🎞️ 전체 박스오피스")

# 표에 보여줄 컬럼 순서
display_df = df[
    [
        "순위",
        "영화명",
        "개봉일",
        "관객수",
        "누적관객",
        "스크린수",
    ]
].copy()


# 숫자를 보기 편하게 표시하기 위한 포맷
# 실제 DataFrame 안의 값은 이미 숫자이므로
# 정렬과 그래프에는 숫자가 그대로 사용됩니다.
display_df["관객수"] = display_df["관객수"].map(
    lambda x: f"{x:,}"
)

display_df["누적관객"] = display_df["누적관객"].map(
    lambda x: f"{x:,}"
)

display_df["스크린수"] = display_df["스크린수"].map(
    lambda x: f"{x:,}"
)


# Streamlit 표로 표시
st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True
)


# --------------------------------------------
# 캐시 안내
# --------------------------------------------
st.caption(
    "💡 같은 날짜의 KOBIS 조회 결과는 약 1시간 동안 캐시됩니다."
)

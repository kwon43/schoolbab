
import streamlit as st
import pandas as pd
import requests
import re
from collections import Counter
import plotly.express as px
from datetime import date, timedelta

# =========================================================
# 🍰 기본 설정
# =========================================================

st.set_page_config(
    page_title="🍰 급식 디저트 연구소",
    page_icon="🍰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================================================
# 🍓 CSS
# =========================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Jua&family=Noto+Sans+KR:wght@400;500;700;900&display=swap');

html, body, [class*="css"] {
    font-family: 'Noto Sans KR', sans-serif;
}

.stApp {
    background: linear-gradient(180deg, #fff7fb 0%, #fffdf8 100%);
}

h1, h2, h3 {
    font-family: 'Jua', sans-serif;
}

.main-title {
    text-align: center;
    font-family: 'Jua', sans-serif;
    font-size: 48px;
    color: #e75480;
    margin-top: 10px;
    margin-bottom: 5px;
}

.sub-title {
    text-align: center;
    color: #9b6879;
    font-size: 18px;
    margin-bottom: 30px;
}

.dessert-card {
    background: white;
    border-radius: 20px;
    padding: 22px;
    margin-bottom: 15px;
    box-shadow: 0 5px 18px rgba(220, 130, 160, 0.12);
    border: 1px solid #ffe1eb;
}

.dessert-card h3 {
    color: #e75480;
    margin-bottom: 8px;
}

.stat-box {
    background: linear-gradient(135deg, #fff0f6, #fff8e9);
    border-radius: 18px;
    padding: 20px;
    text-align: center;
    border: 1px solid #ffdce8;
}

.stat-number {
    font-size: 32px;
    font-weight: 900;
    color: #e75480;
}

.stat-label {
    color: #8f6574;
    font-size: 14px;
}

.stButton > button {
    border-radius: 15px;
    border: none;
    background-color: #f58aaa;
    color: white;
    font-weight: 700;
}

.stButton > button:hover {
    background-color: #e76f95;
    color: white;
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #fff0f6, #fffaf1);
}

.school-select-box {
    background: #fff;
    border: 2px solid #ffd7e4;
    border-radius: 18px;
    padding: 15px;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# 🍮 API 설정
# =========================================================

BASE_URL = "https://open.neis.go.kr/hub"

try:
    API_KEY = st.secrets["NEIS_API_KEY"]
except Exception:
    API_KEY = ""

# =========================================================
# 🍪 디저트 키워드
# =========================================================

DESSERT_KEYWORDS = [
    # 아이스크림 / 유제품
    "아이스크림",
    "아이스",
    "요거트",
    "요구르트",
    "우유",
    "딸기우유",
    "초코우유",
    "바나나우유",

    # 음료
    "주스",
    "쥬스",
    "음료",
    "차",
    "에이드",
    "스무디",

    # 빵 / 과자
    "빵",
    "케이크",
    "케익",
    "쿠키",
    "마카롱",
    "도넛",
    "도너츠",
    "머핀",
    "파이",
    "와플",
    "팬케이크",
    "카스테라",
    "크로플",

    # 떡 / 전통 디저트
    "떡",
    "약과",
    "한과",
    "유과",
    "찹쌀떡",
    "인절미",

    # 디저트
    "푸딩",
    "젤리",
    "젤라틴",
    "초콜릿",
    "초코",
    "사탕",

    # 과일
    "딸기",
    "사과",
    "배",
    "포도",
    "귤",
    "오렌지",
    "수박",
    "참외",
    "바나나",
    "키위",
    "복숭아",
    "파인애플",
    "망고",
    "멜론",
    "블루베리",
    "과일",
    "방울토마토"
]

# =========================================================
# 🍓 API 오류 메시지
# =========================================================

def show_api_error():
    st.error(
        "🍰 NEIS API에서 데이터를 가져오지 못했어요.\n\n"
        "스트림릿 Secrets에 `NEIS_API_KEY`가 제대로 등록되어 있는지 확인해주세요."
    )

# =========================================================
# 🧁 학교 검색
# =========================================================

@st.cache_data(ttl=3600)
def search_schools(school_name):

    if not API_KEY:
        return pd.DataFrame()

    url = f"{BASE_URL}/schoolInfo"

    params = {
        "KEY": API_KEY,
        "Type": "json",
        "pIndex": 1,
        "pSize": 100,
        "SCHUL_NM": school_name.strip()
    }

    try:
        response = requests.get(
            url,
            params=params,
            timeout=15
        )

        response.raise_for_status()
        data = response.json()

        if "schoolInfo" not in data:
            return pd.DataFrame()

        if len(data["schoolInfo"]) < 2:
            return pd.DataFrame()

        rows = data["schoolInfo"][1].get("row", [])

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows)

        return df

    except Exception:
        return pd.DataFrame()


# =========================================================
# 🍩 급식 데이터 가져오기
# =========================================================

@st.cache_data(ttl=1800)
def get_meal_data(
    office_code,
    school_code,
    start_date,
    end_date
):

    if not API_KEY:
        return pd.DataFrame()

    url = f"{BASE_URL}/mealServiceDietInfo"

    params = {
        "KEY": API_KEY,
        "Type": "json",
        "pIndex": 1,
        "pSize": 1000,

        "ATPT_OFCDC_SC_CODE": office_code,
        "SD_SCHUL_CODE": school_code,

        "MLSV_FROM_YMD": start_date,
        "MLSV_TO_YMD": end_date
    }

    try:
        response = requests.get(
            url,
            params=params,
            timeout=20
        )

        response.raise_for_status()

        data = response.json()

        if "mealServiceDietInfo" not in data:
            return pd.DataFrame()

        if len(data["mealServiceDietInfo"]) < 2:
            return pd.DataFrame()

        rows = data["mealServiceDietInfo"][1].get("row", [])

        if not rows:
            return pd.DataFrame()

        return pd.DataFrame(rows)

    except Exception:
        return pd.DataFrame()


# =========================================================
# 🍰 메뉴 나누기
# =========================================================

def split_menu(menu_text):

    if pd.isna(menu_text):
        return []

    text = str(menu_text)

    # <br/> 제거
    text = re.sub(
        r"<br\s*/?>",
        "\n",
        text,
        flags=re.IGNORECASE
    )

    # 알레르기 번호 제거
    text = re.sub(
        r"\([0-9,\.\s]+\)",
        "",
        text
    )

    # 줄바꿈 / 쉼표 / 세미콜론 / 슬래시 기준 분리
    items = re.split(
        r"[\n,;/]+",
        text
    )

    result = []

    for item in items:

        item = item.strip()

        if item:
            result.append(item)

    return result


# =========================================================
# 🍓 디저트 찾기
# =========================================================

def find_desserts(menu_text):

    menu_items = split_menu(menu_text)

    desserts = []

    for item in menu_items:

        clean_item = (
            item
            .replace(" ", "")
            .lower()
        )

        for keyword in DESSERT_KEYWORDS:

            keyword_clean = (
                keyword
                .replace(" ", "")
                .lower()
            )

            if keyword_clean in clean_item:

                desserts.append(item)
                break

    return desserts


# =========================================================
# 🍮 학교별 디저트 분석
# =========================================================

def analyze_school(
    school_name,
    meal_df
):

    if meal_df.empty:

        return {
            "school_name": school_name,
            "desserts": [],
            "counter": Counter(),
            "total": 0,
            "top_dessert": "-",
            "top_count": 0
        }

    dessert_list = []

    for _, row in meal_df.iterrows():

        menu = row.get(
            "DDISH_NM",
            ""
        )

        desserts = find_desserts(menu)

        for dessert in desserts:

            dessert_list.append(
                dessert
            )

    counter = Counter(
        dessert_list
    )

    if counter:

        top_dessert, top_count = (
            counter.most_common(1)[0]
        )

    else:

        top_dessert = "-"
        top_count = 0

    return {
        "school_name": school_name,
        "desserts": dessert_list,
        "counter": counter,
        "total": len(dessert_list),
        "top_dessert": top_dessert,
        "top_count": top_count
    }


# =========================================================
# 🍰 제목
# =========================================================

st.markdown(
    '<div class="main-title">🍰 급식 디저트 연구소 🍓</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="sub-title">'
    '학교별 급식 디저트를 찾아보고 비교해보는 데이터 분석 앱 🍮'
    '</div>',
    unsafe_allow_html=True
)

# =========================================================
# 🍪 API 키 확인
# =========================================================

if not API_KEY:

    st.error(
        "🍰 NEIS_API_KEY가 설정되지 않았어요!"
    )

    st.info(
        "스트림릿 Cloud의 Settings → Secrets에 "
        "`NEIS_API_KEY = \"발급받은키\"` 형식으로 입력해주세요."
    )

    st.stop()


# =========================================================
# 🍓 사이드바
# =========================================================

with st.sidebar:

    st.markdown(
        "## 🍰 디저트 분석 설정"
    )

    st.markdown(
        "---"
    )

    st.markdown(
        "### 🍓 분석 기간"
    )

    today = date.today()

    default_start = today - timedelta(days=30)

    start = st.date_input(
        "시작 날짜",
        value=default_start
    )

    end = st.date_input(
        "끝 날짜",
        value=today
    )

    st.markdown("---")

    st.markdown(
        "### 🍮 분석 방법"
    )

    st.write(
        "급식 메뉴에 디저트 관련 키워드가 "
        "포함되어 있는지를 기준으로 분석합니다."
    )

    st.markdown("---")

    st.caption(
        "🍰 NEIS 학교급식 데이터를 이용합니다."
    )


# =========================================================
# 🍩 날짜 오류 확인
# =========================================================

if start > end:

    st.warning(
        "🍪 시작 날짜가 끝 날짜보다 늦어요. 날짜를 다시 선택해주세요."
    )

    st.stop()


# =========================================================
# 🧁 학교 검색
# =========================================================

st.markdown(
    "## 🍓 1. 학교 검색"
)

search_text = st.text_input(
    "학교 이름을 입력하세요",
    placeholder="예: 서울고, 경기고, 한빛고",
    key="school_search"
)

if search_text.strip():

    with st.spinner("🍰 학교를 찾고 있어요..."):

        school_df = search_schools(
            search_text
        )

    if school_df.empty:

        st.warning(
            "🍪 검색 결과가 없어요. 학교 이름을 다시 입력해주세요."
        )

    else:

        st.success(
            f"🍓 {len(school_df)}개의 학교를 찾았어요!"
        )

        # -------------------------------------------------
        # 학교 선택용 정보 만들기
        # -------------------------------------------------

        school_options = []

        school_mapping = {}

        for index, row in school_df.iterrows():

            school_name = str(
                row.get(
                    "SCHUL_NM",
                    ""
                )
            )

            office_name = str(
                row.get(
                    "ATPT_OFCDC_SC_NM",
                    ""
                )
            )

            school_kind = str(
                row.get(
                    "SCHUL_KND_SC_NM",
                    ""
                )
            )

            location = str(
                row.get(
                    "LCTN_SC_NM",
                    ""
                )
            )

            office_code = str(
                row.get(
                    "ATPT_OFCDC_SC_CODE",
                    ""
                )
            )

            school_code = str(
                row.get(
                    "SD_SCHUL_CODE",
                    ""
                )
            )

            # 같은 이름의 학교가 있을 수 있으므로
            # 지역 + 학교종류를 같이 표시
            display_name = (
                f"{school_name} "
                f"· {location} "
                f"· {school_kind}"
            )

            school_options.append(
                display_name
            )

            school_mapping[
                display_name
            ] = {
                "school_name": school_name,
                "office_name": office_name,
                "school_kind": school_kind,
                "location": location,
                "office_code": office_code,
                "school_code": school_code
            }

        # -------------------------------------------------
        # 🍰 핵심: 여러 학교 선택
        # -------------------------------------------------

        st.markdown(
            "### 🍰 비교할 학교를 선택하세요"
        )

        st.caption(
            "🍓 여러 학교를 선택하면 학교별 디저트 빈도를 한 번에 비교할 수 있어요. "
            "최대 6개까지 선택할 수 있습니다."
        )

        selected_display_names = st.multiselect(
            "학교 선택",
            options=school_options,
            max_selections=6,
            placeholder="비교할 학교를 여러 개 선택하세요 🍰",
            key="selected_schools"
        )

        # -------------------------------------------------
        # 선택 결과
        # -------------------------------------------------

        if selected_display_names:

            st.markdown(
                "### 🍮 선택한 학교"
            )

            cols = st.columns(
                min(len(selected_display_names), 3)
            )

            for i, selected in enumerate(
                selected_display_names
            ):

                info = school_mapping[
                    selected
                ]

                with cols[i % len(cols)]:

                    st.markdown(
                        f"""
                        <div class="dessert-card">
                            <h3>🍰 {info["school_name"]}</h3>
                            <p>🍓 {info["location"]}</p>
                            <p>🍮 {info["school_kind"]}</p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

            # -------------------------------------------------
            # 분석 버튼
            # -------------------------------------------------

            st.markdown("---")

            if st.button(
                "🍰 선택한 학교 디저트 분석하기",
                use_container_width=True
            ):

                st.session_state[
                    "run_analysis"
                ] = True


# =========================================================
# 🍓 분석 실행
# =========================================================

if st.session_state.get(
    "run_analysis",
    False
):

    selected_display_names = st.session_state.get(
        "selected_schools",
        []
    )

    if not selected_display_names:

        st.warning(
            "🍪 먼저 비교할 학교를 선택해주세요!"
        )

        st.stop()

    # -----------------------------------------------------
    # 현재 검색 결과 다시 가져오기
    # -----------------------------------------------------

    school_df = search_schools(
        search_text
    )

    school_mapping = {}

    for _, row in school_df.iterrows():

        school_name = str(
            row.get(
                "SCHUL_NM",
                ""
            )
        )

        location = str(
            row.get(
                "LCTN_SC_NM",
                ""
            )
        )

        school_kind = str(
            row.get(
                "SCHUL_KND_SC_NM",
                ""
            )
        )

        display_name = (
            f"{school_name} "
            f"· {location} "
            f"· {school_kind}"
        )

        school_mapping[
            display_name
        ] = {
            "school_name": school_name,
            "office_code": str(
                row.get(
                    "ATPT_OFCDC_SC_CODE",
                    ""
                )
            ),
            "school_code": str(
                row.get(
                    "SD_SCHUL_CODE",
                    ""
                )
            ),
            "location": location,
            "school_kind": school_kind
        }

    # -----------------------------------------------------
    # 🍰 학교별 분석
    # -----------------------------------------------------

    results = []

    progress = st.progress(0)

    status = st.empty()

    total_schools = len(
        selected_display_names
    )

    for i, display_name in enumerate(
        selected_display_names
    ):

        info = school_mapping.get(
            display_name
        )

        if not info:
            continue

        status.info(
            f"🍓 {info['school_name']}의 급식을 분석하고 있어요..."
        )

        meal_df = get_meal_data(
            info["office_code"],
            info["school_code"],
            start.strftime("%Y%m%d"),
            end.strftime("%Y%m%d")
        )

        analysis = analyze_school(
            info["school_name"],
            meal_df
        )

        analysis[
            "location"
        ] = info["location"]

        analysis[
            "school_kind"
        ] = info["school_kind"]

        results.append(
            analysis
        )

        progress.progress(
            (i + 1) / total_schools
        )

    status.empty()
    progress.empty()

    # -----------------------------------------------------
    # 분석 결과 없음
    # -----------------------------------------------------

    if not results:

        st.error(
            "🍪 분석할 학교 데이터를 찾지 못했어요."
        )

        st.stop()

    # =====================================================
    # 🍮 분석 결과
    # =====================================================

    st.markdown("---")

    st.markdown(
        "## 🍰 분석 결과"
    )

    st.markdown(
        f"### 🍓 {start.strftime('%Y-%m-%d')} ~ "
        f"{end.strftime('%Y-%m-%d')}"
    )

    # =====================================================
    # 🍩 전체 통계 카드
    # =====================================================

    total_desserts = sum(
        result["total"]
        for result in results
    )

    most_dessert_school = max(
        results,
        key=lambda x: x["total"]
    )

    cols = st.columns(3)

    with cols[0]:

        st.markdown(
            f"""
            <div class="stat-box">
                <div class="stat-number">
                    {len(results)}
                </div>
                <div class="stat-label">
                    🍰 분석한 학교 수
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with cols[1]:

        st.markdown(
            f"""
            <div class="stat-box">
                <div class="stat-number">
                    {total_desserts}
                </div>
                <div class="stat-label">
                    🍓 전체 디저트 등장 횟수
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with cols[2]:

        st.markdown(
            f"""
            <div class="stat-box">
                <div class="stat-number">
                    {most_dessert_school["school_name"]}
                </div>
                <div class="stat-label">
                    🍮 디저트가 가장 많이 나온 학교
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # =====================================================
    # 🍰 학교별 디저트 빈도 비교
    # =====================================================

    st.markdown("---")

    st.markdown(
        "## 🍰 학교별 디저트 등장 횟수 비교"
    )

    comparison_data = []

    for result in results:

        comparison_data.append(
            {
                "학교": result[
                    "school_name"
                ],
                "디저트 등장 횟수": result[
                    "total"
                ]
            }
        )

    comparison_df = pd.DataFrame(
        comparison_data
    )

    fig = px.bar(
        comparison_df,
        x="학교",
        y="디저트 등장 횟수",
        text="디저트 등장 횟수",
        title="🍓 학교별 디저트 등장 횟수",
        labels={
            "학교": "학교",
            "디저트 등장 횟수": "등장 횟수"
        }
    )

    fig.update_traces(
        textposition="outside"
    )

    fig.update_layout(
        height=500,
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # =====================================================
    # 🍮 학교별 TOP 디저트
    # =====================================================

    st.markdown("---")

    st.markdown(
        "## 🍮 학교별 가장 많이 나온 디저트"
    )

    top_data = []

    for result in results:

        if result["counter"]:

            top_desserts = (
                result["counter"]
                .most_common(10)
            )

            for dessert, count in top_desserts:

                top_data.append(
                    {
                        "학교": result[
                            "school_name"
                        ],
                        "디저트": dessert,
                        "횟수": count
                    }
                )

    if top_data:

        top_df = pd.DataFrame(
            top_data
        )

        fig_top = px.bar(
            top_df,
            x="횟수",
            y="디저트",
            color="학교",
            orientation="h",
            title="🍓 학교별 디저트 TOP 10",
            labels={
                "횟수": "등장 횟수",
                "디저트": "디저트"
            }
        )

        fig_top.update_layout(
            height=max(
                500,
                len(top_df) * 25
            ),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)"
        )

        st.plotly_chart(
            fig_top,
            use_container_width=True
        )

    # =====================================================
    # 🧁 학교별 1위 디저트 카드
    # =====================================================

    st.markdown("---")

    st.markdown(
        "## 🧁 학교별 디저트 1위"
    )

    result_cols = st.columns(
        min(len(results), 3)
    )

    for i, result in enumerate(
        results
    ):

        with result_cols[
            i % len(result_cols)
        ]:

            if result["top_dessert"] != "-":

                st.markdown(
                    f"""
                    <div class="dessert-card">
                        <h3>🍰 {result["school_name"]}</h3>

                        <p>
                            🍓 가장 많이 나온 디저트
                        </p>

                        <h2 style="color:#e75480;">
                            🍮 {result["top_dessert"]}
                        </h2>

                        <p>
                            등장 횟수:
                            <strong>
                                {result["top_count"]}회
                            </strong>
                        </p>

                        <p>
                            전체 디저트:
                            <strong>
                                {result["total"]}회
                            </strong>
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            else:

                st.markdown(
                    f"""
                    <div class="dessert-card">
                        <h3>🍰 {result["school_name"]}</h3>
                        <p>🍪 분석 기간에 디저트가 발견되지 않았어요.</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

    # =====================================================
    # 🍓 상세 데이터 표
    # =====================================================

    st.markdown("---")

    st.markdown(
        "## 🍓 학교별 분석표"
    )

    summary_data = []

    for result in results:

        summary_data.append(
            {
                "학교": result[
                    "school_name"
                ],
                "지역": result[
                    "location"
                ],
                "학교 종류": result[
                    "school_kind"
                ],
                "디저트 등장 횟수": result[
                    "total"
                ],
                "가장 많이 나온 디저트": result[
                    "top_dessert"
                ],
                "1위 등장 횟수": result[
                    "top_count"
                ]
            }
        )

    summary_df = pd.DataFrame(
        summary_data
    )

    st.dataframe(
        summary_df,
        use_container_width=True,
        hide_index=True
    )

    # =====================================================
    # 🍰 디저트별 상세 빈도
    # =====================================================

    st.markdown("---")

    st.markdown(
        "## 🍰 학교별 디저트 상세 빈도"
    )

    for result in results:

        st.markdown(
            f"### 🍮 {result['school_name']}"
        )

        if result["counter"]:

            detail_data = []

            for dessert, count in (
                result["counter"]
                .most_common()
            ):

                detail_data.append(
                    {
                        "디저트": dessert,
                        "등장 횟수": count
                    }
                )

            detail_df = pd.DataFrame(
                detail_data
            )

            st.dataframe(
                detail_df,
                use_container_width=True,
                hide_index=True
            )

        else:

            st.info(
                "🍪 이 기간에는 디저트가 발견되지 않았어요."
            )

    # =====================================================
    # 🍓 다운로드
    # =====================================================

    st.markdown("---")

    st.markdown(
        "## 🍓 분석 결과 저장"
    )

    csv_data = summary_df.to_csv(
        index=False,
        encoding="utf-8-sig"
    )

    st.download_button(
        label="🍰 분석 결과 CSV 다운로드",
        data=csv_data,
        file_name="school_dessert_analysis.csv",
        mime="text/csv",
        use_container_width=True
    )

    # =====================================================
    # 🍮 주의사항
    # =====================================================

    st.markdown("---")

    st.markdown(
        """
        <div class="dessert-card">

        <h3>🍰 분석 방법 안내</h3>

        <p>
        이 앱은 NEIS 급식 메뉴에서 디저트와 관련된
        단어를 찾아 디저트 등장 횟수를 계산합니다.
        </p>

        <p>
        🍓 따라서 과일이나 우유처럼 학교에 따라
        디저트로 분류할 수도 있고 반찬·식품으로
        분류할 수도 있는 메뉴가 포함될 수 있습니다.
        </p>

        <p>
        🍮 데이터 분석 결과는 설정한 기간과
        NEIS에 등록된 급식 메뉴를 기준으로 합니다.
        </p>

        </div>
        """,
        unsafe_allow_html=True
    )


# =========================================================
# 🍪 화면 하단
# =========================================================

st.markdown("---")

st.markdown(
    """
    <div style="text-align:center; color:#b27b8d;">
        🍰🍓🍮 급식 속 디저트를 데이터로 만나보세요 🍮🍓🍰
    </div>
    """,
    unsafe_allow_html=True
)

# =========================================================
# 🍰 디저트 풍선 효과
# =========================================================

if st.session_state.get(
    "run_analysis",
    False
):

    st.balloons()
```

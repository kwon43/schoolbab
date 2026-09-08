```python
import streamlit as st
import pandas as pd
import requests
import re
from collections import Counter
from datetime import date, timedelta
import plotly.express as px

# =========================================================
# 기본 설정
# =========================================================

st.set_page_config(
    page_title="🍰 급식 디저트 연구소",
    page_icon="🍰",
    layout="wide"
)

BASE_URL = "https://open.neis.go.kr/hub"

# =========================================================
# NEIS API KEY
# =========================================================

try:
    API_KEY = st.secrets["NEIS_API_KEY"]
except Exception:
    API_KEY = ""

# =========================================================
# 디자인
# =========================================================

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Jua&family=Noto+Sans+KR:wght@400;700;900&display=swap');

    html, body, [class*="css"] {
        font-family: 'Noto Sans KR', sans-serif;
    }

    .stApp {
        background: linear-gradient(
            180deg,
            #fff5fa 0%,
            #fffdf8 100%
        );
    }

    h1, h2, h3 {
        font-family: 'Jua', sans-serif;
    }

    .title {
        text-align: center;
        font-family: 'Jua', sans-serif;
        font-size: 48px;
        color: #e85b88;
        margin-top: 20px;
    }

    .subtitle {
        text-align: center;
        color: #9d7180;
        font-size: 18px;
        margin-bottom: 30px;
    }

    .card {
        background: white;
        border-radius: 20px;
        padding: 22px;
        margin: 10px 0;
        border: 1px solid #ffdce8;
        box-shadow: 0 5px 18px rgba(220, 130, 160, 0.12);
    }

    .number {
        font-size: 34px;
        font-weight: 900;
        color: #e85b88;
    }

    .label {
        color: #8e6876;
    }

    .stButton > button {
        border-radius: 15px;
        background-color: #f28aae;
        color: white;
        border: none;
        font-weight: 700;
    }

    .stButton > button:hover {
        background-color: #e66d95;
        color: white;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(
            180deg,
            #fff0f6,
            #fffaf0
        );
    }
    </style>
    """,
    unsafe_allow_html=True
)

# =========================================================
# 디저트 판별 키워드
# =========================================================

DESSERT_KEYWORDS = [
    "아이스크림",
    "요거트",
    "요구르트",
    "우유",
    "주스",
    "쥬스",
    "에이드",
    "스무디",

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
    "카스테라",
    "크로플",

    "떡",
    "약과",
    "한과",
    "유과",
    "찹쌀떡",
    "인절미",

    "푸딩",
    "젤리",
    "초콜릿",
    "사탕",

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
    "과일"
]

# =========================================================
# API 함수
# =========================================================

@st.cache_data(ttl=3600)
def search_schools(school_name):

    url = f"{BASE_URL}/schoolInfo"

    params = {
        "KEY": API_KEY,
        "Type": "json",
        "pIndex": 1,
        "pSize": 100,
        "SCHUL_NM": school_name
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

        rows = data["schoolInfo"][1].get(
            "row",
            []
        )

        return pd.DataFrame(rows)

    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=1800)
def get_meal_data(
    office_code,
    school_code,
    start_date,
    end_date
):

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

        rows = data["mealServiceDietInfo"][1].get(
            "row",
            []
        )

        return pd.DataFrame(rows)

    except Exception:
        return pd.DataFrame()

# =========================================================
# 메뉴 처리
# =========================================================

def split_menu(menu):

    if pd.isna(menu):
        return []

    text = str(menu)

    text = re.sub(
        r"<br\s*/?>",
        "\n",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"\([0-9,\.\s]+\)",
        "",
        text
    )

    items = re.split(
        r"[\n,;/]+",
        text
    )

    return [
        item.strip()
        for item in items
        if item.strip()
    ]


def find_desserts(menu):

    items = split_menu(menu)

    desserts = []

    for item in items:

        clean = (
            item
            .replace(" ", "")
            .lower()
        )

        for keyword in DESSERT_KEYWORDS:

            key = (
                keyword
                .replace(" ", "")
                .lower()
            )

            if key in clean:
                desserts.append(item)
                break

    return desserts


# =========================================================
# 학교 분석
# =========================================================

def analyze_school(
    school_name,
    meal_df
):

    counter = Counter()

    if meal_df.empty:

        return {
            "school": school_name,
            "counter": counter,
            "total": 0
        }

    for _, row in meal_df.iterrows():

        menu = row.get(
            "DDISH_NM",
            ""
        )

        desserts = find_desserts(menu)

        for dessert in desserts:
            counter[dessert] += 1

    total = sum(counter.values())

    return {
        "school": school_name,
        "counter": counter,
        "total": total
    }


# =========================================================
# API KEY 확인
# =========================================================

if not API_KEY:

    st.error(
        "🍰 NEIS_API_KEY가 설정되지 않았어요."
    )

    st.info(
        "Streamlit Cloud → Settings → Secrets에서 "
        "NEIS_API_KEY를 설정해주세요."
    )

    st.stop()


# =========================================================
# 제목
# =========================================================

st.markdown(
    '<div class="title">🍰 급식 디저트 연구소 🍓</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    '학교 급식 데이터를 이용해 디저트를 비교해보는 데이터 분석 앱 🍮'
    '</div>',
    unsafe_allow_html=True
)

# =========================================================
# 사이드바
# =========================================================

with st.sidebar:

    st.markdown("## 🍰 분석 설정")

    today = date.today()

    start_date = st.date_input(
        "🍓 시작 날짜",
        today - timedelta(days=30)
    )

    end_date = st.date_input(
        "🍮 끝 날짜",
        today
    )

    st.markdown("---")

    st.markdown("### 🍪 분석 기준")

    st.write(
        "NEIS의 실제 급식 메뉴인 "
        "`DDISH_NM`을 가져온 뒤 "
        "디저트 관련 키워드가 포함된 메뉴를 분석합니다."
    )


# =========================================================
# 날짜 확인
# =========================================================

if start_date > end_date:

    st.warning(
        "🍰 시작 날짜가 끝 날짜보다 늦습니다."
    )

    st.stop()


# =========================================================
# 학교 검색
# =========================================================

st.markdown("## 🍓 1. 학교 검색")

school_name_input = st.text_input(
    "학교 이름을 입력하세요",
    placeholder="예: 서울고, 경기고, 한빛고"
)

# =========================================================
# 검색
# =========================================================

if school_name_input.strip():

    with st.spinner("🍰 학교를 찾는 중이에요..."):

        school_df = search_schools(
            school_name_input.strip()
        )

    if school_df.empty:

        st.warning(
            "🍪 검색된 학교가 없습니다."
        )

    else:

        st.success(
            f"🍓 {len(school_df)}개의 학교를 찾았습니다!"
        )

        # -------------------------------------------------
        # 학교 정보 정리
        # -------------------------------------------------

        school_options = []
        school_info = {}

        for index, row in school_df.iterrows():

            name = str(
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

            # 학교를 구분하기 위해
            # 지역 + 종류까지 표시
            display = (
                f"{name} | "
                f"{location} | "
                f"{school_kind}"
            )

            school_options.append(
                display
            )

            school_info[display] = {
                "name": name,
                "location": location,
                "school_kind": school_kind,
                "office_code": office_code,
                "school_code": school_code
            }

        # -------------------------------------------------
        # 여러 학교 선택
        # -------------------------------------------------

        st.markdown(
            "### 🍰 2. 비교할 학교를 선택하세요"
        )

        st.caption(
            "🍓 여러 학교를 선택해서 동시에 비교할 수 있습니다. "
            "최대 6개까지 선택할 수 있어요."
        )

        selected_schools = st.multiselect(
            "학교 선택",
            school_options,
            max_selections=6,
            placeholder="학교를 여러 개 선택하세요 🍮"
        )

        # -------------------------------------------------
        # 선택 학교 표시
        # -------------------------------------------------

        if selected_schools:

            st.markdown(
                "### 🍩 선택한 학교"
            )

            selected_cols = st.columns(
                min(3, len(selected_schools))
            )

            for i, selected in enumerate(
                selected_schools
            ):

                info = school_info[selected]

                with selected_cols[
                    i % len(selected_cols)
                ]:

                    st.markdown(
                        f"""
                        <div class="card">
                            <h3>🍰 {info["name"]}</h3>
                            <p>🍓 지역: {info["location"]}</p>
                            <p>🍮 학교 종류: {info["school_kind"]}</p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

            # -------------------------------------------------
            # 분석 버튼
            # -------------------------------------------------

            if st.button(
                "🍰 선택한 학교 분석하기",
                use_container_width=True
            ):

                st.session_state[
                    "analysis_started"
                ] = True

                st.session_state[
                    "selected_schools_data"
                ] = selected_schools

# =========================================================
# 분석
# =========================================================

if st.session_state.get(
    "analysis_started",
    False
):

    selected_schools = st.session_state.get(
        "selected_schools_data",
        []
    )

    if not selected_schools:

        st.warning(
            "🍪 학교를 먼저 선택해주세요."
        )

        st.stop()

    # 현재 검색 결과에서 정보 다시 만들기
    school_df = search_schools(
        school_name_input.strip()
    )

    school_info = {}

    for _, row in school_df.iterrows():

        name = str(
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

        display = (
            f"{name} | "
            f"{location} | "
            f"{school_kind}"
        )

        school_info[display] = {
            "name": name,
            "location": location,
            "school_kind": school_kind,
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
            )
        }

    # -----------------------------------------------------
    # 학교별 데이터 가져오기
    # -----------------------------------------------------

    results = []

    progress = st.progress(0)

    for i, selected in enumerate(
        selected_schools
    ):

        info = school_info.get(
            selected
        )

        if info is None:
            continue

        st.write(
            f"🍓 {info['name']} 급식을 분석하고 있어요..."
        )

        meal_df = get_meal_data(
            info["office_code"],
            info["school_code"],
            start_date.strftime("%Y%m%d"),
            end_date.strftime("%Y%m%d")
        )

        result = analyze_school(
            info["name"],
            meal_df
        )

        result["location"] = info[
            "location"
        ]

        result["school_kind"] = info[
            "school_kind"
        ]

        results.append(result)

        progress.progress(
            (i + 1) / len(selected_schools)
        )

    progress.empty()

    # =====================================================
    # 결과
    # =====================================================

    st.markdown("---")

    st.markdown(
        "## 🍮 분석 결과"
    )

    st.write(
        f"🍰 분석 기간: "
        f"{start_date} ~ {end_date}"
    )

    # -----------------------------------------------------
    # 통계
    # -----------------------------------------------------

    total_desserts = sum(
        r["total"]
        for r in results
    )

    if results:

        best_school = max(
            results,
            key=lambda x: x["total"]
        )

    else:

        best_school = None

    stat_cols = st.columns(3)

    with stat_cols[0]:

        st.markdown(
            f"""
            <div class="card">
                <div class="number">
                    {len(results)}
                </div>
                <div class="label">
                    🍰 분석 학교 수
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with stat_cols[1]:

        st.markdown(
            f"""
            <div class="card">
                <div class="number">
                    {total_desserts}
                </div>
                <div class="label">
                    🍓 전체 디저트 등장 횟수
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with stat_cols[2]:

        best_name = (
            best_school["school"]
            if best_school
            else "-"
        )

        st.markdown(
            f"""
            <div class="card">
                <div class="number">
                    {best_name}
                </div>
                <div class="label">
                    🍮 디저트가 가장 많이 나온 학교
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # =====================================================
    # 학교별 디저트 빈도
    # =====================================================

    st.markdown("---")

    st.markdown(
        "## 🍰 학교별 디저트 등장 횟수"
    )

    comparison = pd.DataFrame(
        [
            {
                "학교": r["school"],
                "디저트 등장 횟수": r["total"]
            }
            for r in results
        ]
    )

    if not comparison.empty:

        fig = px.bar(
            comparison,
            x="학교",
            y="디저트 등장 횟수",
            text="디저트 등장 횟수",
            title="🍓 학교별 디저트 빈도 비교"
        )

        fig.update_traces(
            textposition="outside"
        )

        fig.update_layout(
            height=500,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    # =====================================================
    # 학교별 가장 많이 나온 디저트
    # =====================================================

    st.markdown("---")

    st.markdown(
        "## 🍮 학교별 최다 디저트"
    )

    top_rows = []

    for result in results:

        if result["counter"]:

            top_dessert, top_count = (
                result["counter"]
                .most_common(1)[0]
            )

        else:

            top_dessert = "-"
            top_count = 0

        top_rows.append(
            {
                "학교": result["school"],
                "가장 많이 나온 디저트": top_dessert,
                "등장 횟수": top_count
            }
        )

    top_df = pd.DataFrame(
        top_rows
    )

    st.dataframe(
        top_df,
        use_container_width=True,
        hide_index=True
    )

    # =====================================================
    # 학교별 TOP 10 디저트
    # =====================================================

    st.markdown("---")

    st.markdown(
        "## 🍓 학교별 디저트 TOP 10"
    )

    detail_rows = []

    for result in results:

        for dessert, count in (
            result["counter"]
            .most_common(10)
        ):

            detail_rows.append(
                {
                    "학교": result["school"],
                    "디저트": dessert,
                    "등장 횟수": count
                }
            )

    detail_df = pd.DataFrame(
        detail_rows
    )

    if not detail_df.empty:

        fig2 = px.bar(
            detail_df,
            x="등장 횟수",
            y="디저트",
            color="학교",
            orientation="h",
            title="🍰 학교별 디저트 TOP 10"
        )

        fig2.update_layout(
            height=max(
                500,
                len(detail_df) * 25
            ),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)"
        )

        st.plotly_chart(
            fig2,
            use_container_width=True
        )

    else:

        st.info(
            "🍪 분석 기간에 디저트로 분류된 메뉴가 없습니다."
        )

    # =====================================================
    # 상세 학교별 결과
    # =====================================================

    st.markdown("---")

    st.markdown(
        "## 🧁 학교별 상세 결과"
    )

    for result in results:

        st.markdown(
            f"### 🍰 {result['school']}"
        )

        if result["counter"]:

            rows = [
                {
                    "디저트": dessert,
                    "등장 횟수": count
                }
                for dessert, count
                in result["counter"].most_common()
            ]

            df = pd.DataFrame(rows)

            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True
            )

        else:

            st.info(
                "🍪 디저트가 발견되지 않았습니다."
            )

    # =====================================================
    # CSV 다운로드
    # =====================================================

    st.markdown("---")

    st.markdown(
        "## 🍰 결과 저장"
    )

    csv = top_df.to_csv(
        index=False,
        encoding="utf-8-sig"
    )

    st.download_button(
        "🍓 분석 결과 CSV 다운로드",
        data=csv,
        file_name="school_dessert_analysis.csv",
        mime="text/csv",
        use_container_width=True
    )

    # =====================================================
    # 안내
    # =====================================================

    st.markdown("---")

    st.markdown(
        """
        <div class="card">

        <h3>🍮 분석 기준</h3>

        <p>
        이 앱은 NEIS에서 제공하는 실제 학교급식 메뉴의
        <b>DDISH_NM</b> 데이터를 이용합니다.
        </p>

        <p>
        🍓 메뉴에 디저트 관련 키워드가 포함되어 있는 경우
        디저트로 분류합니다.
        </p>

        <p>
        🍰 따라서 과일이나 우유처럼 상황에 따라
        디저트가 아닐 수도 있는 메뉴가 포함될 수 있습니다.
        </p>

        </div>
        """,
        unsafe_allow_html=True
    )

# =========================================================
# 하단
# =========================================================

st.markdown("---")

st.markdown(
    """
    <div style="
        text-align:center;
        color:#b47789;
        padding:20px;
        font-size:16px;
    ">
        🍰 🍓 🍮 🧁 🍪 🍩 🍨
        <br>
        급식 속 달콤한 데이터를 찾아보세요
        <br>
        🍨 🍩 🍪 🧁 🍮 🍓 🍰
    </div>
    """,
    unsafe_allow_html=True
)
```

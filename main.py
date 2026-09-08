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
    page_icon="🍓",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =========================================================
# 디자인
# =========================================================

st.markdown("""
<style>

@import url('https://fonts.googleapis.com/css2?family=Jua&family=Noto+Sans+KR:wght@400;500;700;900&display=swap');

html, body, [class*="css"] {
    font-family: 'Noto Sans KR', sans-serif;
}

.stApp {
    background: linear-gradient(
        135deg,
        #fff5fa 0%,
        #fff9f3 50%,
        #fff0f7 100%
    );
}

/* 제목 */
.main-title {
    text-align: center;
    padding: 25px 10px 10px 10px;
}

.main-title h1 {
    font-family: 'Jua', sans-serif;
    color: #e75480;
    font-size: 48px;
    margin-bottom: 5px;
}

.main-title p {
    color: #9c6475;
    font-size: 18px;
}

/* 카드 */
.info-card {
    background: rgba(255,255,255,0.9);
    border: 2px solid #ffd6e5;
    border-radius: 22px;
    padding: 22px;
    margin: 10px 0;
    box-shadow: 0 6px 18px rgba(231,84,128,0.08);
}

.result-card {
    background: linear-gradient(
        135deg,
        #ffffff,
        #fff3f8
    );
    border: 2px solid #ffc8dc;
    border-radius: 22px;
    padding: 20px;
    text-align: center;
    box-shadow: 0 7px 20px rgba(231,84,128,0.10);
}

.result-card h3 {
    color: #d94b78;
    margin-bottom: 10px;
}

.result-number {
    font-size: 36px;
    font-weight: 900;
    color: #e75480;
}

.dessert-name {
    font-size: 20px;
    font-weight: 700;
    color: #7c4a5c;
}

.section-title {
    font-family: 'Jua', sans-serif;
    color: #d94b78;
    font-size: 30px;
    margin-top: 25px;
}

div.stButton > button {
    background: linear-gradient(
        90deg,
        #ff8fb3,
        #ffb6c9
    );
    color: white;
    border: none;
    border-radius: 15px;
    font-weight: 700;
    padding: 10px 22px;
}

div.stButton > button:hover {
    background: linear-gradient(
        90deg,
        #e75480,
        #ff8fb3
    );
    color: white;
}

[data-testid="stSidebar"] {
    background: #fff0f6;
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# 제목
# =========================================================

st.markdown("""
<div class="main-title">
    <h1>🍰 급식 디저트 연구소 🍓</h1>
    <p>학교마다 어떤 디저트가 가장 많이 나올까? 🧁</p>
</div>
""", unsafe_allow_html=True)


# =========================================================
# API KEY
# =========================================================

try:
    API_KEY = st.secrets["NEIS_API_KEY"]
except Exception:
    API_KEY = ""


if not API_KEY:
    st.warning(
        "🔑 NEIS API 인증키가 설정되지 않았어요. "
        "Streamlit Cloud의 Secrets에 NEIS_API_KEY를 입력해주세요."
    )


BASE_URL = "https://open.neis.go.kr/hub"


# =========================================================
# 디저트 키워드
# =========================================================

DESSERT_KEYWORDS = [
    "아이스크림",
    "아이스",
    "요구르트",
    "요거트",
    "우유",
    "초코우유",
    "딸기우유",
    "바나나우유",
    "주스",
    "쥬스",
    "음료",
    "푸딩",
    "젤리",
    "케이크",
    "롤케이크",
    "카스텔라",
    "카스테라",
    "쿠키",
    "마카롱",
    "도넛",
    "도너츠",
    "머핀",
    "와플",
    "팬케이크",
    "핫케이크",
    "파이",
    "타르트",
    "과일",
    "사과",
    "배",
    "귤",
    "오렌지",
    "바나나",
    "포도",
    "딸기",
    "수박",
    "참외",
    "복숭아",
    "키위",
    "멜론",
    "방울토마토",
    "토마토",
    "찐옥수수",
    "옥수수",
    "떡",
    "인절미",
    "꿀떡",
    "송편",
    "약과",
    "한과",
    "팥빙수",
    "빙수",
    "초콜릿",
    "초코",
]


# =========================================================
# 학교 검색
# =========================================================

@st.cache_data(ttl=3600)
def search_schools(school_name):

    if not API_KEY or not school_name.strip():
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

        rows = data["schoolInfo"][1]["row"]

        df = pd.DataFrame(rows)

        wanted_columns = [
            "ATPT_OFCDC_SC_CODE",
            "ATPT_OFCDC_SC_NM",
            "SD_SCHUL_CODE",
            "SCHUL_NM",
            "SCHUL_KND_SC_NM",
            "LCTN_SC_NM"
        ]

        existing = [
            col for col in wanted_columns
            if col in df.columns
        ]

        return df[existing]

    except Exception:
        return pd.DataFrame()


# =========================================================
# 급식 데이터 가져오기
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

        rows = data["mealServiceDietInfo"][1]["row"]

        return pd.DataFrame(rows)

    except Exception:
        return pd.DataFrame()


# =========================================================
# 메뉴 분리
# =========================================================

def split_menu(menu_text):

    if not isinstance(menu_text, str):
        return []

    # <br/> 등 HTML 제거
    menu_text = re.sub(
        r"<br\s*/?>",
        "\n",
        menu_text,
        flags=re.IGNORECASE
    )

    # 알레르기 번호 제거
    menu_text = re.sub(
        r"\([0-9,\.\s]+\)",
        "",
        menu_text
    )

    # 특수문자를 기준으로 분리
    items = re.split(
        r"[\n,;/]+",
        menu_text
    )

    cleaned = []

    for item in items:

        item = item.strip()

        if item:
            cleaned.append(item)

    return cleaned


# =========================================================
# 디저트 판별
# =========================================================

def find_desserts(menu_text):

    menus = split_menu(menu_text)

    desserts = []

    for menu in menus:

        menu_without_space = menu.replace(" ", "")

        for keyword in DESSERT_KEYWORDS:

            if keyword in menu_without_space:

                desserts.append(menu)

                break

    return desserts


# =========================================================
# 학교별 분석
# =========================================================

def analyze_school(
    school_info,
    start_date,
    end_date
):

    office_code = school_info["ATPT_OFCDC_SC_CODE"]
    school_code = school_info["SD_SCHUL_CODE"]
    school_name = school_info["SCHUL_NM"]

    df = get_meal_data(
        office_code,
        school_code,
        start_date,
        end_date
    )

    if df.empty:
        return {
            "school": school_name,
            "meal_data": pd.DataFrame(),
            "desserts": [],
            "counter": Counter()
        }

    all_desserts = []

    for _, row in df.iterrows():

        menu = row.get("DDISH_NM", "")

        desserts = find_desserts(menu)

        all_desserts.extend(desserts)

    counter = Counter(all_desserts)

    return {
        "school": school_name,
        "meal_data": df,
        "desserts": all_desserts,
        "counter": counter
    }


# =========================================================
# 사이드바
# =========================================================

with st.sidebar:

    st.markdown("## 🍓 분석 설정")

    st.markdown(
        "### 🏫 학교 찾기"
    )

    school_search = st.text_input(
        "학교명을 입력하세요",
        placeholder="예: 서울고등학교"
    )

    if st.button(
        "🔍 학교 검색",
        use_container_width=True
    ):

        if school_search.strip():

            with st.spinner("🏫 학교를 찾고 있어요..."):

                school_df = search_schools(
                    school_search
                )

            if school_df.empty:

                st.error(
                    "😢 학교를 찾지 못했어요."
                )

            else:

                st.session_state["school_results"] = school_df

                st.success(
                    f"🍰 {len(school_df)}개의 학교를 찾았어요!"
                )

    st.markdown("---")

    st.markdown("### 📅 분석 기간")

    default_start = date.today() - timedelta(days=90)

    start_date = st.date_input(
        "시작일",
        value=default_start
    )

    end_date = st.date_input(
        "종료일",
        value=date.today()
    )

    st.markdown("---")

    st.markdown("""
    ### 💗 분석 방법

    급식 메뉴 중 미리 정한 디저트
    키워드에 해당하는 메뉴를 찾아서

    🍰 제공 횟수  
    🏆 가장 많이 나온 디저트  
    📊 학교별 차이

    를 비교합니다.
    """)


# =========================================================
# 학교 선택
# =========================================================

if "school_results" not in st.session_state:

    st.markdown("""
    <div class="info-card">

    <h2>🍓 먼저 학교를 검색해주세요!</h2>

    <p>
    왼쪽에서 학교 이름을 검색하면<br>
    여러 학교를 선택해서 디저트 제공 빈도를 비교할 수 있어요. 🧁
    </p>

    </div>
    """, unsafe_allow_html=True)

    st.stop()


school_df = st.session_state["school_results"].copy()


# 학교 선택용 표시 이름
school_options = {}

for _, row in school_df.iterrows():

    name = row["SCHUL_NM"]

    location = row.get(
        "LCTN_SC_NM",
        ""
    )

    kind = row.get(
        "SCHUL_KND_SC_NM",
        ""
    )

    label = f"{name} · {location} · {kind}"

    school_options[label] = row.to_dict()


st.markdown(
    '<div class="section-title">🏫 비교할 학교를 골라주세요</div>',
    unsafe_allow_html=True
)

selected_labels = st.multiselect(
    "여러 학교를 선택할 수 있어요.",
    options=list(school_options.keys()),
    max_selections=6,
    placeholder="학교를 선택하세요 🍰"
)


if not selected_labels:

    st.info(
        "👆 최소 1개의 학교를 선택해주세요."
    )

    st.stop()


if start_date > end_date:

    st.error(
        "⚠️ 시작일이 종료일보다 늦을 수 없어요."
    )

    st.stop()


# =========================================================
# 분석 시작
# =========================================================

if st.button(
    "🍰 디저트 분석 시작!",
    use_container_width=True
):

    results = []

    progress = st.progress(0)

    status = st.empty()

    for index, label in enumerate(selected_labels):

        school_info = school_options[label]

        status.info(
            f"🧁 {school_info['SCHUL_NM']}의 급식을 분석하고 있어요..."
        )

        result = analyze_school(
            school_info,
            start_date.strftime("%Y%m%d"),
            end_date.strftime("%Y%m%d")
        )

        results.append(result)

        progress.progress(
            (index + 1) / len(selected_labels)
        )

    status.success(
        "🎉 분석이 완료됐어요!"
    )

    st.session_state["analysis_results"] = results

    st.balloons()


# =========================================================
# 결과 출력
# =========================================================

if "analysis_results" not in st.session_state:

    st.info(
        "🍓 위의 **디저트 분석 시작!** 버튼을 눌러주세요."
    )

    st.stop()


results = st.session_state["analysis_results"]


# =========================================================
# 결과 데이터 만들기
# =========================================================

summary_rows = []

for result in results:

    counter = result["counter"]

    total_count = sum(counter.values())

    if counter:

        top_dessert, top_count = counter.most_common(1)[0]

    else:

        top_dessert = "없음"
        top_count = 0

    summary_rows.append({
        "학교": result["school"],
        "디저트 제공 횟수": total_count,
        "가장 많이 나온 디저트": top_dessert,
        "최다 제공 횟수": top_count
    })


summary_df = pd.DataFrame(summary_rows)


# =========================================================
# 전체 결과
# =========================================================

st.markdown(
    '<div class="section-title">🍰 학교별 분석 결과</div>',
    unsafe_allow_html=True
)


# 결과 카드
columns = st.columns(len(summary_df))


for col, (_, row) in zip(
    columns,
    summary_df.iterrows()
):

    with col:

        st.markdown(
            f"""
            <div class="result-card">

            <h3>🏫 {row['학교']}</h3>

            <div class="result-number">
                {row['디저트 제공 횟수']}회
            </div>

            <p>🍰 디저트 제공</p>

            <div class="dessert-name">
                🏆 {row['가장 많이 나온 디저트']}
            </div>

            <p>
                가장 많이 나온 디저트<br>
                <b>{row['최다 제공 횟수']}회</b>
            </p>

            </div>
            """,
            unsafe_allow_html=True
        )


# =========================================================
# 학교별 빈도 비교
# =========================================================

st.markdown(
    '<div class="section-title">📊 학교별 디저트 제공 횟수 비교</div>',
    unsafe_allow_html=True
)


chart_df = summary_df.sort_values(
    "디저트 제공 횟수",
    ascending=False
)


fig = px.bar(
    chart_df,
    x="학교",
    y="디저트 제공 횟수",
    text="디저트 제공 횟수",
    title="🍰 학교별 디저트 제공 횟수",
    labels={
        "학교": "학교",
        "디저트 제공 횟수": "제공 횟수"
    }
)

fig.update_traces(
    textposition="outside",
    marker_color="#F58BA8"
)

fig.update_layout(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(
        family="Noto Sans KR",
        size=14
    ),
    title_font_size=22,
    title_font_color="#D94B78",
    xaxis_title="학교",
    yaxis_title="디저트 제공 횟수",
    hovermode="x unified"
)

st.plotly_chart(
    fig,
    use_container_width=True
)


# =========================================================
# 학교별 최다 디저트
# =========================================================

st.markdown(
    '<div class="section-title">🏆 학교별 인기 디저트</div>',
    unsafe_allow_html=True
)


for result in results:

    counter = result["counter"]

    if not counter:

        st.warning(
            f"😢 {result['school']}에서는 "
            "분류된 디저트를 찾지 못했어요."
        )

        continue

    top_items = counter.most_common(10)

    dessert_df = pd.DataFrame(
        top_items,
        columns=[
            "디저트",
            "제공 횟수"
        ]
    )

    st.markdown(
        f"### 🏫 {result['school']}"
    )

    top_name, top_count = top_items[0]

    st.success(
        f"🥇 가장 많이 나온 디저트는 "
        f"**{top_name}** — **{top_count}회**예요!"
    )

    fig2 = px.bar(
        dessert_df,
        x="제공 횟수",
        y="디저트",
        orientation="h",
        text="제공 횟수",
        title=f"🍩 {result['school']} 디저트 TOP 10",
        labels={
            "제공 횟수": "제공 횟수",
            "디저트": "디저트"
        }
    )

    fig2.update_traces(
        textposition="outside",
        marker_color="#FFB6C9"
    )

    fig2.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(
            family="Noto Sans KR",
            size=13
        ),
        title_font_color="#D94B78",
        yaxis={
            "categoryorder": "total ascending"
        }
    )

    st.plotly_chart(
        fig2,
        use_container_width=True
    )


# =========================================================
# 전체 비교표
# =========================================================

st.markdown(
    '<div class="section-title">📋 한눈에 보는 비교</div>',
    unsafe_allow_html=True
)

display_df = summary_df.copy()

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True
)


# =========================================================
# 안내
# =========================================================

st.markdown("""
<div class="info-card">

### 🍓 분석할 때 알아두세요!

이 웹앱은 급식 메뉴의 이름을 기준으로
디저트를 분류합니다.

예를 들어 `아이스크림`, `요구르트`, `과일`,
`케이크`, `쿠키`, `우유` 등의 메뉴가
디저트로 분류됩니다.

따라서 학교에서 제공하는 메뉴 이름에 따라
실제 디저트와 분류 결과가 조금 다를 수 있습니다. 🧁

</div>
""", unsafe_allow_html=True)

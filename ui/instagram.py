import streamlit as st
from st_on_hover_tabs import on_hover_tabs
from utils.helpers import *

# def sidebar():
#     with st.sidebar:
#         # tabs = on_hover_tabs(tabName=['랜딩 페이지', '북마크 추가', '북마크 검색'], 
#         #                     iconName=['home', 'bookmark', 'search'],
#         #                     styles = {'navtab': {'background-color':'#000',
#         #                                         'color': '#ffffff',
#         #                                         'font-size': '10px',
#         #                                         'transition': '.3s',
#         #                                         'white-space': 'nowrap',
#         #                                         'text-transform': 'uppercase'},
#         #                             'tabStyle': {':hover :hover': {'color': 'red',
#         #                                                             'cursor': 'pointer'}},
#         #                             'tabStyle' : {'list-style-type': 'none',
#         #                                             'margin-bottom': '30px',
#         #                                             'padding-left': '30px'},
#         #                             'iconStyle':{'position':'fixed',
#         #                                             'left':'7.5px',
#         #                                             'text-align': 'left'},
#         #                             },
#         #                     key="0")
#         tabs = on_hover_tabs(tabName=['랜딩 페이지', '북마크 추가', '북마크 검색'], 
#                             iconName=['home', 'bookmark', 'search'],
#                             styles = {
#                                 'navtab': {
#                                     'background-color': '#000',
#                                     'color': '#ffffff',
#                                     'font-size': '10px',
#                                     'transition': '.3s',
#                                     'white-space': 'nowrap',
#                                     'text-transform': 'uppercase'
#                                 },
#                                 'tabStyle': {
#                                     'list-style-type': 'none',
#                                     'margin-bottom': '30px',
#                                     'padding-left': '30px'
#                                 },
#                                 'hoverTabStyle': {
#                                     'color': 'yellow',
#                                     'cursor': 'pointer'
#                                 },
#                                 'iconStyle': {
#                                     'position': 'fixed',
#                                     'left': '7.5px',
#                                     'text-align': 'left'
#                                 }
#                             },
#                             key="0")
#         # tabs = on_hover_tabs(tabName=['랜딩 페이지', '북마크 추가', '북마크 검색'], 
#         #                     iconName=['home', 'bookmark', 'search'], default_choice=0)
#     return tabs

# 인스타그램 스타일 CSS 추가
def load_css():
    st.markdown("""
    <style>
    /* 라이트 테마 설정 */
    body {
        background-color: #FAFAFA;
        color: #262626;
    }
    
    /* 전체 앱 스타일 */
    .main {
        background-color: #fafafa;
        padding: 0;
        max-width: 100%;
    }
    
    /* 사이드바 스타일 - 여러 클래스 선택자 사용 */
    .css-1544g2n {  /* Streamlit 사이드바 클래스 */
        background-color: white !important;
        border-right: 1px solid #dbdbdb;
        padding: 1rem 0.25rem !important;
        width: 55px !important;
        min-width: 55px !important;
        position: fixed;
        max-width: 55px !important;
    }
    
    div[data-testid="stSidebar"] {
        background-color: white !important;
        width: 55px !important;
        min-width: 55px !important;
        max-width: 55px !important;
    }
    
    .css-6qob1r {
        width: 55px !important;
        min-width: 55px !important;
    }
    
    /* 사이드바 내부 여백 제거 */
    .css-hxt7ib {
        padding-top: 2rem;
        padding-left: 0.5rem;
        padding-right: 0.5rem;
    }
    
    /* 사이드바 확장 화살표 제거 */
    button[kind="header"] {
        display: none !important;
    }
    
    /* 헤더와 기타 Streamlit 기본 요소 스타일 */
    .css-18ni7ap {
        background-color: white;
        color: #262626;
    }
    
    .css-fg4pbf {
        background-color: white;
    }
    
    /* 버튼 스타일 */
    .css-1x8cf1d {
        background-color: #0095f6;
        color: white;
    }
    
    /* 콘텐츠 영역 - 사이드바 너비만큼 여백 조정 */
    .main .block-container {
        padding-left: 70px;
        max-width: 100%;
    }
    
    /* 피드 컨테이너 */
    .feed-container {
        max-width: 600px;
        margin: 20px auto;
        background-color: white;
        border: 1px solid #dbdbdb;
        border-radius: 3px;
    }
    
    /* 인스타그램 피드 스타일 */
    .feed-header {
        display: flex;
        align-items: center;
        padding: 14px 16px;
        border-bottom: 1px solid #efefef;
    }
    
    .feed-header-user {
        font-weight: 600;
        margin-left: 10px;
    }
    
    .feed-image {
        width: 100%;
    }
    
    .feed-actions {
        display: flex;
        padding: 8px 16px;
    }
    
    .feed-action-icon {
        margin-right: 16px;
        cursor: pointer;
    }
    
    .feed-likes {
        padding: 0 16px;
        margin-bottom: 8px;
        font-weight: 600;
    }
    
    .feed-caption {
        padding: 0 16px;
        margin-bottom: 8px;
    }
    
    .feed-time {
        padding: 0 16px;
        color: #8e8e8e;
        font-size: 12px;
        margin-bottom: 16px;
    }
    
    /* 검색 영역 */
    .search-container {
        display: flex;
        background-color: white;
        border: 1px solid #dbdbdb;
        border-radius: 3px;
        margin-bottom: 20px;
        padding: 10px;
    }
    
    /* 로그인 폼 */
    .login-container {
        max-width: 350px;
        margin: 100px auto;
        background-color: white;
        border: 1px solid #dbdbdb;
        border-radius: 3px;
        padding: 30px;
        text-align: center;
    }
    
    .instagram-logo {
        font-family: 'Instagram Sans', 'Arial', cursive;
        font-size: 36px;
        margin-bottom: 20px;
    }
    
    /* 버튼 스타일 */
    .instagram-button {
        background-color: #0095f6;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 8px 16px;
        font-weight: 600;
        cursor: pointer;
        width: 100%;
    }
    
    .instagram-button:hover {
        background-color: #1877f2;
    }
    
    /* 그리드 레이아웃 */
    .grid-container {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        grid-gap: 15px;
    }
    
    .grid-item {
        aspect-ratio: 1;
        position: relative;
        overflow: hidden;
    }
    
    .grid-item img {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }
    
    /* 피드 네비게이션 버튼 */
    .feed-nav-button {
        position: absolute;
        top: 50%;
        transform: translateY(-50%);
        background-color: white;
        border-radius: 50%;
        width: 30px;
        height: 30px;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 1px 2px rgba(0,0,0,0.2);
        cursor: pointer;
        z-index: 10;
    }
    
    .nav-next {
        right: 10px;
    }
    
    .nav-prev {
        left: 10px;
    }
    
    /* 카테고리 태그 */
    .category-tag {
        display: inline-block;
        background-color: #efefef;
        padding: 4px 8px;
        border-radius: 4px;
        margin-right: 8px;
        margin-bottom: 8px;
        font-size: 12px;
    }
    </style>
    """, unsafe_allow_html=True)

def load_sidebar_css():
    # 간소화된 사이드바 스타일 설정
    sidebar_css = """
    <style>
    /* 사이드바 기본 스타일 */
    [data-testid="stSidebar"] {
        background-color: white !important;
        border-right: 1px solid #dbdbdb;
        width: 100px !important;
        min-width: 110px !important;
        max-width: 120px !important;
    }
    
    /* 사이드바 내부 여백 조정 */
    [data-testid="stSidebarContent"] {
        padding-top: 1rem;
        padding-left: 0.5rem;
        padding-right: 0.5rem;
    }
    
    /* 사이드바 버튼 스타일링 */
    div.stSidebar div.stButton > button {
        width: 46px !important;
        height: 46px !important;
        border-radius: 50% !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        background-color: white !important;
        border: none !important;
        margin: 10px auto !important;
        font-size: 22px !important;
        padding: 0 !important;
        transition: all 0.2s;
        /* 이모지를 흑백으로 변경하는 필터 추가 */
        filter: grayscale(80%) !important;
    }

    div.stSidebar div.stButton > button:hover {
        background-color: #f8f8f8;
        transform: scale(1.1);
        /* 호버 시 컬러로 변경 (선택 사항) */
        filter: grayscale(0%);
    }
    
    /* 사이드바 현재 메뉴 강조 */
    div.stSidebar div.stButton button[kind="secondary"] {
        color: #0095f6;
    }
    
    /* 사이드바 확장 화살표 제거 */
    button[kind="header"] {
        display: none !important;
    }
    
    /* 콘텐츠 영역 조정 */
    .main .block-container {
        padding-left: 80px !important;
        max-width: calc(100% - 80px);
    }
    
    /* 전체 앱 배경색 */
    .main {
        background-color: #fafafa;
    }
    </style>
    """
    
    # 현재 선택된 메뉴 확인 (세션 상태 사용)
    current_menu = st.session_state["current_menu"]

    # 활성 메뉴 표시를 위한 JavaScript
    active_menu_js = f"""
    <script>
    document.addEventListener('DOMContentLoaded', function() {{
        // 현재 활성화된 메뉴 버튼에 스타일 적용
        const currentMenu = "{current_menu}";
        let activeButton = null;
        
        if (currentMenu === "랜딩 페이지") {{
            activeButton = document.querySelector('[data-testid="stSidebar"] div.stButton > button[key="btn_home"]');
        }} else if (currentMenu === "북마크 추가") {{
            activeButton = document.querySelector('[data-testid="stSidebar"] div.stButton > button[key="btn_bookmark"]');
        }} else if (currentMenu === "북마크 검색") {{
            activeButton = document.querySelector('[data-testid="stSidebar"] div.stButton > button[key="btn_search"]');
        }}
        
        if (activeButton) {{
            activeButton.style.color = '#0095f6';
            activeButton.style.fontWeight = 'bold';
        }}
    }});
    </script>
    """
    
    # CSS와 JavaScript 적용
    st.sidebar.markdown(sidebar_css, unsafe_allow_html=True)
    st.sidebar.markdown(active_menu_js, unsafe_allow_html=True)

# 사이드바 메뉴 정의
def sidebar_menu():
    # Font Awesome 아이콘 CSS 추가 및 세션 상태 초기화
    st.sidebar.markdown("""
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
    """, unsafe_allow_html=True)
    
    # 현재 선택된 메뉴 확인 (세션 상태 사용)
    current_menu = st.session_state["current_menu"]
    
    # 아이콘 활성화 상태 설정
    home_active = "active" if current_menu == "랜딩 페이지" else ""
    bookmark_active = "active" if current_menu == "북마크 추가" else ""
    search_active = "active" if current_menu == "북마크 검색" else ""

    # 직접 Streamlit 버튼 생성 (메뉴 항목마다 하나의 버튼)
    st.sidebar.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # 홈 버튼
    st.sidebar.button("🏠", on_click=change_menu, args=("랜딩 페이지",))
    
    # 북마크 버튼
    st.sidebar.button("🔖", on_click=change_menu, args=("북마크 추가",))
    
    # 검색 버튼
    if st.sidebar.button("🔍", key="btn_search"):
        st.session_state["current_menu"] = "북마크 검색"
        # st.query_params.menu = "북마크 검색"
        # if 'search_input' in st.session_state:
        #     st.session_state.search_input = ""
        st.session_state["search_input"] = ""
        st.rerun()

    # 추천 버튼
    st.sidebar.button("👍", on_click=change_menu, args=("추천 페이지",))
    

# 쿼리 파라미터에서 세션 상태로 메뉴 상태 동기화
def sync_session_state_from_query_params():
    query_params = st.query_params
    if "menu" in query_params:
        current_menu = query_params.get("menu")
        st.session_state["current_menu"] = current_menu

def setup_page():
    # CSS 로드
    # load_css()
    load_sidebar_css()
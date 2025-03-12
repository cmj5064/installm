import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from datetime import datetime

class DashboardUI:
    def __init__(self, db):
        """대시보드 UI 초기화
        
        Args:
            db: 데이터베이스 관리자 인스턴스
        """
        self.db = db
    
    def show(self):
        """북마크 대시보드 표시"""
        st.header("북마크 대시보드")
        
        # 통계 불러오기
        conn = sqlite3.connect(self.db.db_path)
        
        # 북마크 개수
        total_bookmarks = pd.read_sql("SELECT COUNT(*) as count FROM bookmarks", conn).iloc[0]['count']
        
        # 카테고리 통계
        category_counts = pd.read_sql("""
        SELECT c.name, COUNT(bc.bookmark_id) as count
        FROM categories c
        JOIN bookmark_categories bc ON c.id = bc.category_id
        GROUP BY c.name
        ORDER BY count DESC
        LIMIT 10
        """, conn)
        
        # 시간별 통계
        time_stats = pd.read_sql("""
        SELECT 
            strftime('%Y-%m', taken_at) as month, 
            COUNT(*) as count
        FROM bookmarks
        GROUP BY month
        ORDER BY month
        """, conn)
        
        conn.close()
        
        # 대시보드 레이아웃
        col1, col2, col3 = st.columns(3)
        
        # 기본 통계
        with col1:
            st.metric("총 북마크 수", total_bookmarks)
        
        with col2:
            total_categories = len(self.db.get_categories())
            st.metric("카테고리 수", total_categories)
        
        with col3:
            st.metric("첫 북마크 저장일", time_stats['month'].iloc[0] if not time_stats.empty else "데이터 없음")
        
        # 카테고리 분포
        st.subheader("카테고리 분포")
        if not category_counts.empty:
            fig = px.bar(category_counts, x='name', y='count', title="상위 카테고리")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("카테고리 데이터가 없습니다.")
            
        # 시간별 북마크 추세
        st.subheader("월별 북마크 수")
        if not time_stats.empty:
            fig = px.line(time_stats, x='month', y='count', title="월별 북마크 수")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("날짜 데이터가 없습니다.")
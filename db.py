import sqlite3
import os
import logging
from typing import List, Dict, Optional, Any, Tuple, Optional
import json
import streamlit as st

class BookmarkDatabase:
    """SQLite 데이터베이스 관리 클래스"""

    def __init__(self, db_path: str):
        """데이터베이스 초기화
        
        Args:
            db_path: 데이터베이스 파일 경로
        """
        self.db_path = db_path
        self.logger = logging.getLogger("Database")
        
        # 데이터베이스 디렉토리 확인 및 생성
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
            
        # 데이터베이스 연결 및 테이블 생성
        self._initialize_db()
        
    def _initialize_db(self) -> None:
        """필요한 테이블을 생성합니다."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 북마크 테이블 생성
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            collection_id TEXT,
            feed_id TEXT,
            media_type TEXT,
            caption TEXT,
            media_url TEXT,
            thumbnail_url TEXT,
            thumbnail TEXT,
            url TEXT,
            hashtags TEXT,
            category TEXT,
            category_reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # thumbnail 컬럼 추가 (없는 경우에만)
        try:
            cursor.execute("ALTER TABLE bookmarks ADD COLUMN thumbnail TEXT")
            self.logger.info("thumbnail 컬럼 추가 완료")
        except sqlite3.OperationalError:
            # 컬럼이 이미 존재하는 경우 무시
            pass

        # 카테고리 테이블 생성
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # 기본 카테고리 추가
        default_categories = ["여행", "맛집", "영화", "공연", "개구리"]
        for category in default_categories:
            try:
                cursor.execute("INSERT INTO categories (name) VALUES (?)", (category,))
            except sqlite3.IntegrityError:
                pass  # 이미 존재하는 카테고리는 무시

        conn.commit()
        conn.close()
        
    def _get_connection(self) -> sqlite3.Connection:
        """데이터베이스 연결을 반환합니다.
        
        Returns:
            SQLite 데이터베이스 연결 객체
        """
        return sqlite3.connect(self.db_path)
    
    def _check_bookmark_exists(self, cursor, feed_id: str) -> Optional[int]:
        """북마크가 이미 데이터베이스에 존재하는지 확인합니다.
        
        Args:
            cursor: 데이터베이스 커서
            feed_id: 확인할 피드 ID
            
        Returns:
            북마크가 존재하면 해당 ID 반환, 없으면 None 반환
        """
        if not feed_id:
            self.logger.warning("feed_id가 없는, 확인 불가능한 북마크")
            return None
            
        cursor.execute("SELECT id FROM bookmarks WHERE feed_id = ?", (feed_id,))
        existing = cursor.fetchone()
        
        if existing:
            return existing[0] # bookmark_id: int
        return None

    def add_bookmark_batch(self, bookmarks: List[dict], categorize_agent=None) -> Tuple[int, int]:
        """북마크 목록을 일괄적으로 추가하고 자동으로 카테고리를 분류합니다.
        
        Args:
            bookmarks: 북마크 목록
            categorize_agent: 카테고리 분류 에이전트 (선택 사항)
            
        Returns:
            (성공한 항목 수, 실패한 항목 수) 튜플
        """
        if not bookmarks:
            return (0, 0)
        
        success_count = 0
        fail_count = 0

        conn = self._get_connection()
        try:
            # 트랜잭션 시작
            conn.execute('BEGIN IMMEDIATE')  # 명시적으로 락을 획득하여 충돌 방지
            cursor = conn.cursor()

            # 1단계: 카테고리 분류 (북마크 저장 전 수행)
            if categorize_agent:
                # Streamlit UI가 있는 경우 진행 상황 표시
                progress_bar = None
                if 'st' in globals() and hasattr(st, 'progress'):
                    # 빈 컨테이너 생성
                    info_container = st.empty()
                    info_container.info("카테고리 자동 분류 중...")
                    progress_bar = st.progress(0)
                
                total_items = len(bookmarks)
                
                # 각 북마크별로 카테고리 분류
                for i, bookmark in enumerate(bookmarks):
                    # 기존에 저장된 feed인지 확인
                    feed_id = bookmark.get('feed_id')
                    if not feed_id:
                        self.logger.warning("feed_id가 없는 북마크는 카테고리 생성 건너뜀")
                        continue
                    # cursor.execute("SELECT id FROM bookmarks WHERE feed_id = ?", (feed_id,))
                    # existing = cursor.fetchone()
                    
                    # if not existing:
                    bookmark_id = self._check_bookmark_exists(cursor, feed_id)
                    if not bookmark_id:
                        try:
                            caption = bookmark.get('caption', '')
                            
                            # 해시태그가 JSON 문자열로 저장되어 있으면 다시 파싱
                            hashtags = bookmark.get('hashtags', [])
                            if isinstance(hashtags, str):
                                try:
                                    hashtags = json.loads(hashtags)
                                except:
                                    hashtags = []
                            
                            # 카테고리 분류
                            try:
                                response = categorize_agent.classify(
                                    caption=caption,
                                    hashtags=hashtags
                                )
                                bookmark['category'] = response.categories
                                bookmark['category_reason'] = response.category_reason
                                # 기존 st.info 대신 info_container 업데이트
                                if 'st' in globals() and hasattr(st, 'info') and 'info_container' in locals():
                                    info_container.info(f"카테고리 자동 분류 중...: {bookmark['category']}")
                            except Exception as e:
                                self.logger.error(f"북마크 카테고리 분류 중 오류: {str(e)}")
                                if 'st' in globals() and hasattr(st, 'warning'):
                                    st.warning(f"북마크 카테고리 분류 중 오류: {str(e)}")
                                bookmark['category'] = "기타"
                                bookmark['category_reason'] = f"카테고리 분류 중 오류 발생: {str(e)}"
                        
                        except Exception as e:
                            self.logger.error(f"북마크 처리 중 오류: {str(e)}")
                            bookmark['category'] = "기타"
                            bookmark['category_reason'] = f"처리 중 오류: {str(e)}"
                    
                    # 진행상황 업데이트
                    if progress_bar:
                        progress_bar.progress((i + 1) / total_items)
                
                # 진행 완료
                if progress_bar:
                    progress_bar.progress(100)
                    if 'info_container' in locals():
                        info_container.success("카테고리 분류 완료!")
                    else:
                        st.success("카테고리 분류 완료!")
            
            # 2단계: 북마크 저장 (카테고리 포함하여 저장)
            for bookmark in bookmarks:
                try:
                    feed_id = bookmark.get('feed_id')
                    if not feed_id:
                        self.logger.warning("feed_id가 없는 북마크 건너뜀")
                        fail_count += 1
                        continue
                    
                    # # 이미 존재하는지 확인
                    # cursor.execute("SELECT id FROM bookmarks WHERE feed_id = ?", (feed_id,))
                    # existing = cursor.fetchone()
                    
                    # if existing:
                    bookmark_id = self._check_bookmark_exists(cursor, feed_id)
                    if bookmark_id:
                        # # 이미 존재하면 업데이트만 수행 (카테고리 정보 업데이트)
                        # bookmark_id = existing[0]
                        
                        # # 카테고리 정보가 있으면 업데이트
                        # if 'category' in bookmark:
                        #     category = bookmark.get('category', '기타')
                        #     category_reason = bookmark.get('category_reason', '')
                            
                        #     cursor.execute('''
                        #     UPDATE bookmarks 
                        #     SET category = ?, category_reason = ?
                        #     WHERE id = ?
                        #     ''', (category, category_reason, bookmark_id))
                            
                        #     # 카테고리 테이블에도 추가 (이미 있으면 무시)
                        #     cursor.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (category,))
                        
                        # self.logger.info(f"이미 존재하는 북마크 카테고리 업데이트: ID {bookmark_id}")
                        pass
                    else:
                        # 해시태그는 JSON으로 저장
                        bookmark_copy = bookmark.copy()  # 원본 데이터 보존
                        if 'hashtags' in bookmark_copy and isinstance(bookmark_copy['hashtags'], list):
                            bookmark_copy['hashtags'] = json.dumps(bookmark_copy['hashtags'], ensure_ascii=False)
                        
                        # 카테고리 정보가 없으면 기본값 설정
                        if 'category' not in bookmark_copy:
                            bookmark_copy['category'] = "기타"
                            bookmark_copy['category_reason'] = ""
                        
                        # 카테고리 테이블에 추가 (이미 있으면 무시)
                        cursor.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (bookmark_copy['category'],))
                            
                        # 새로 추가 (카테고리 포함)
                        cursor.execute('''
                        INSERT INTO bookmarks (collection_id, feed_id, media_type, caption, media_url, thumbnail_url, url, hashtags, category, category_reason)
                        VALUES (:collection_id, :feed_id, :media_type, :caption, :media_url, :thumbnail_url, :url, :hashtags, :category, :category_reason)
                        ''', bookmark_copy)
                        
                        bookmark_id = cursor.lastrowid
                        self.logger.info(f"북마크 저장됨: ID {bookmark_id}")
                    
                    success_count += 1
                except Exception as e:
                    self.logger.error(f"북마크 저장 중 오류 발생: {e}")
                    fail_count += 1
                    continue  # 현재 북마크 처리에 실패해도 다음 북마크 계속 처리
                
                # 트랜잭션 커밋
                conn.commit()
            
        except Exception as e:
            if conn:
                conn.rollback()
            self.logger.error(f"북마크 일괄 추가 실패: {e}")
            return (success_count, fail_count)
        finally:
            if conn:
                conn.close()
        
        self.logger.info(f"북마크 {success_count}개 일괄 처리 완료 (실패: {fail_count}개)")
        return (success_count, fail_count)
    
    def categorize_bookmark_batch(self, bookmarks: List[dict], categorize_agent) -> Tuple[int, int]:
        """북마크 목록을 일괄적으로 카테고리를 분류합니다.
        
        Args:
            bookmarks: 북마크 목록
            categorize_agent: 카테고리 분류 에이전트
            
        Returns:
            (성공한 항목 수, 실패한 항목 수) 튜플
        """
        if not bookmarks:
            return (0, 0)
        
        success_count = 0
        fail_count = 0

        conn = self._get_connection()
        try:
            # 트랜잭션 시작
            conn.execute('BEGIN IMMEDIATE')  # 명시적으로 락을 획득하여 충돌 방지
            cursor = conn.cursor()

            # 1단계: 카테고리 분류 (북마크 저장 전 수행)
            if categorize_agent:
                # Streamlit UI가 있는 경우 진행 상황 표시
                progress_bar = None
                if 'st' in globals() and hasattr(st, 'progress'):
                    # 빈 컨테이너 생성
                    info_container = st.empty()
                    info_container.info("카테고리 자동 분류 중...")
                    progress_bar = st.progress(0)
                
                total_items = len(bookmarks)
                
                # 각 북마크별로 카테고리 분류
                for i, bookmark in enumerate(bookmarks):
                    # 기존에 저장된 feed인지 확인
                    feed_id = bookmark.get('feed_id')
                    if not feed_id:
                        self.logger.warning("feed_id가 없는 북마크는 카테고리 생성 건너뜀")
                        continue
                    # cursor.execute("SELECT id FROM bookmarks WHERE feed_id = ?", (feed_id,))
                    # existing = cursor.fetchone()
                    
                    # if not existing:
                    bookmark_id = self._check_bookmark_exists(cursor, feed_id)
                    if bookmark_id:
                        try:
                            caption = bookmark.get('caption', '')
                            
                            # 해시태그가 JSON 문자열로 저장되어 있으면 다시 파싱
                            hashtags = bookmark.get('hashtags', [])
                            if isinstance(hashtags, str):
                                try:
                                    hashtags = json.loads(hashtags)
                                except:
                                    hashtags = []
                            
                            # 카테고리 분류
                            try:
                                response = categorize_agent.classify(
                                    caption=caption,
                                    hashtags=hashtags
                                )
                                bookmark['category'] = response.categories
                                bookmark['category_reason'] = response.category_reason
                                # 기존 st.info 대신 info_container 업데이트
                                if 'st' in globals() and hasattr(st, 'info') and 'info_container' in locals():
                                    info_container.info(f"카테고리 자동 분류 중...: {bookmark['category']}")
                            except Exception as e:
                                self.logger.error(f"북마크 카테고리 분류 중 오류: {str(e)}")
                                if 'st' in globals() and hasattr(st, 'warning'):
                                    st.warning(f"북마크 카테고리 분류 중 오류: {str(e)}")
                                bookmark['category'] = "기타"
                                bookmark['category_reason'] = f"카테고리 분류 중 오류 발생: {str(e)}"
                        
                        except Exception as e:
                            self.logger.error(f"북마크 처리 중 오류: {str(e)}")
                            bookmark['category'] = "기타"
                            bookmark['category_reason'] = f"처리 중 오류: {str(e)}"
                    
                    # 진행상황 업데이트
                    if progress_bar:
                        progress_bar.progress((i + 1) / total_items)
                
                # 진행 완료
                if progress_bar:
                    progress_bar.progress(100)
                    if 'info_container' in locals():
                        info_container.success("카테고리 분류 완료!")
                    else:
                        st.success("카테고리 분류 완료!")
            
            # 2단계: 북마크 저장 (카테고리 포함하여 저장)
            for bookmark in bookmarks:
                try:
                    feed_id = bookmark.get('feed_id')
                    if not feed_id:
                        self.logger.warning("feed_id가 없는 북마크 건너뜀")
                        fail_count += 1
                        continue
                    
                    bookmark_id = self._check_bookmark_exists(cursor, feed_id)
                    if bookmark_id:
                        # 이미 존재하면 업데이트만 수행 (카테고리 정보 업데이트)
                        if 'category' in bookmark:
                            category = bookmark.get('category', '기타')
                            category_reason = bookmark.get('category_reason', '')
                            
                            cursor.execute('''
                            UPDATE bookmarks 
                            SET category = ?, category_reason = ?
                            WHERE id = ?
                            ''', (category, category_reason, bookmark_id))
                            
                            # 카테고리 테이블에도 추가 (이미 있으면 무시)
                            cursor.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (category,))
                        
                        self.logger.info(f"이미 존재하는 북마크 카테고리 업데이트: ID {bookmark_id}")
                        pass
                    else:
                        # 해시태그는 JSON으로 저장
                        bookmark_copy = bookmark.copy()  # 원본 데이터 보존
                        if 'hashtags' in bookmark_copy and isinstance(bookmark_copy['hashtags'], list):
                            bookmark_copy['hashtags'] = json.dumps(bookmark_copy['hashtags'], ensure_ascii=False)
                        
                        # 카테고리 정보가 없으면 기본값 설정
                        if 'category' not in bookmark_copy:
                            bookmark_copy['category'] = "기타"
                            bookmark_copy['category_reason'] = ""
                        
                        # 카테고리 테이블에 추가 (이미 있으면 무시)
                        cursor.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (bookmark_copy['category'],))
                            
                        # 새로 추가 (카테고리 포함)
                        cursor.execute('''
                        INSERT INTO bookmarks (collection_id, feed_id, media_type, caption, media_url, thumbnail_url, url, hashtags, category, category_reason)
                        VALUES (:collection_id, :feed_id, :media_type, :caption, :media_url, :thumbnail_url, :url, :hashtags, :category, :category_reason)
                        ''', bookmark_copy)
                        
                        bookmark_id = cursor.lastrowid
                        self.logger.info(f"북마크 저장됨: ID {bookmark_id}")
                    
                    success_count += 1
                except Exception as e:
                    self.logger.error(f"북마크 저장 중 오류 발생: {e}")
                    fail_count += 1
                    continue  # 현재 북마크 처리에 실패해도 다음 북마크 계속 처리
                
                # 트랜잭션 커밋
                conn.commit()
            
        except Exception as e:
            if conn:
                conn.rollback()
            self.logger.error(f"북마크 일괄 추가 실패: {e}")
            return (success_count, fail_count)
        finally:
            if conn:
                conn.close()
        
        self.logger.info(f"북마크 {success_count}개 일괄 처리 완료 (실패: {fail_count}개)")
        return (success_count, fail_count)

    def get_bookmarks(self, collection_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """북마크 목록을 가져옵니다.
        
        Args:
            collection_id: 필터링할 컬렉션 ID (선택 사항)
            limit: 최대 결과 수
            
        Returns:
            북마크 목록
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            query = "SELECT * FROM bookmarks"
            params = []
            
            if collection_id:
                query += " WHERE collection_id = ?"
                params.append(collection_id)
                
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            columns = [desc[0] for desc in cursor.description]
            results = []
            
            for row in cursor.fetchall():
                item = dict(zip(columns, row))
                
                # 해시태그 JSON 파싱
                if item.get('hashtags'):
                    try:
                        item['hashtags'] = json.loads(item['hashtags'])
                    except json.JSONDecodeError:
                        item['hashtags'] = []
                
                results.append(item)
                
            return results
            
        except sqlite3.Error as e:
            self.logger.error(f"북마크 가져오기 실패: {e}")
            return []
            
        finally:
            conn.close()
    
    def delete_bookmark(self, bookmark_id: int) -> bool:
        """북마크를 삭제합니다.
        
        Args:
            bookmark_id: 삭제할 북마크 ID
            
        Returns:
            삭제 성공 여부
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM bookmarks WHERE id = ?", (bookmark_id,))
            conn.commit()
            
            if cursor.rowcount > 0:
                self.logger.info(f"북마크 삭제됨: ID {bookmark_id}")
                return True
            else:
                self.logger.warning(f"삭제할 북마크를 찾을 수 없음: ID {bookmark_id}")
                return False
                
        except sqlite3.Error as e:
            conn.rollback()
            self.logger.error(f"북마크 삭제 실패: {e}")
            return False
            
        finally:
            conn.close()
    
    def search_bookmarks(self, query: str) -> List[Dict[str, Any]]:
        """북마크를 검색합니다.
        
        Args:
            query: 검색어
            
        Returns:
            검색 결과 북마크 목록
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # 캡션과 해시태그에서 검색
            search_param = f"%{query}%"
            cursor.execute('''
            SELECT * FROM bookmarks
            WHERE caption LIKE ? OR hashtags LIKE ?
            ORDER BY created_at DESC
            ''', (search_param, search_param))
            
            columns = [desc[0] for desc in cursor.description]
            results = []
            
            for row in cursor.fetchall():
                item = dict(zip(columns, row))
                
                # 해시태그 JSON 파싱
                if item.get('hashtags'):
                    try:
                        item['hashtags'] = json.loads(item['hashtags'])
                    except json.JSONDecodeError:
                        item['hashtags'] = []
                
                results.append(item)
                
            return results
            
        except sqlite3.Error as e:
            self.logger.error(f"북마크 검색 실패: {e}")
            return []
            
        finally:
            conn.close()
    
    def get_collections(self) -> List[Tuple[str, int]]:
        """저장된 컬렉션 ID 목록과 각 컬렉션의 항목 수를 가져옵니다.
        
        Returns:
            컬렉션 ID와 항목 수의 튜플 목록
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            SELECT collection_id, COUNT(*) as count
            FROM bookmarks
            WHERE collection_id IS NOT NULL AND collection_id != ''
            GROUP BY collection_id
            ORDER BY count DESC
            ''')
            
            return cursor.fetchall()
            
        except sqlite3.Error as e:
            self.logger.error(f"컬렉션 목록 가져오기 실패: {e}")
            return []
            
        finally:
            conn.close()

    def add_category(self, name: str) -> int:
        """새로운 카테고리를 추가합니다.
        
        Args:
            name: 카테고리 이름
            
        Returns:
            카테고리 ID
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            INSERT INTO categories (name)
            VALUES (?)
            ''', (name,))
            
            category_id = cursor.lastrowid
            conn.commit()
            self.logger.info(f"카테고리 추가됨: {name}")
            return category_id
            
        except sqlite3.IntegrityError:
            # 이미 존재하는 카테고리인 경우 ID 반환
            cursor.execute("SELECT id FROM categories WHERE name = ?", (name,))
            return cursor.fetchone()[0]
            
        except sqlite3.Error as e:
            conn.rollback()
            self.logger.error(f"카테고리 추가 실패: {e}")
            return -1
            
        finally:
            conn.close()

    def get_all_categories(self) -> List[str]:
        """모든 카테고리 목록을 가져옵니다.
        
        Returns:
            카테고리 이름 목록
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT name FROM categories ORDER BY name")
            return [row[0] for row in cursor.fetchall()]
            
        except sqlite3.Error as e:
            self.logger.error(f"카테고리 목록 가져오기 실패: {e}")
            return []
            
        finally:
            conn.close()

    def get_bookmark_categories(self, bookmark_id: int) -> List[Dict[str, Any]]:
        """북마크의 카테고리 정보를 가져옵니다.
        
        Args:
            bookmark_id: 북마크 ID
            
        Returns:
            카테고리 정보 목록 (이름과 분류 이유)
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            SELECT category, caption, category_reason
            FROM bookmarks
            WHERE id = ?
            ''', (bookmark_id,))
            
            row = cursor.fetchone()
            if row:
                return [{
                    'name': row[0],
                    'caption': row[1],
                    'reason': row[2]
                }]
            return []
            
        except sqlite3.Error as e:
            self.logger.error(f"북마크 카테고리 가져오기 실패: {e}")
            return []
            
        finally:
            conn.close()

    def get_bookmarks_by_category(self, category_name: str) -> List[Dict[str, Any]]:
        """특정 카테고리의 북마크 목록을 가져옵니다.
        
        Args:
            category_name: 카테고리 이름
            
        Returns:
            북마크 목록
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            SELECT *
            FROM bookmarks
            WHERE category = ?
            ORDER BY created_at DESC
            ''', (category_name,))
            
            columns = [desc[0] for desc in cursor.description]
            results = []
            
            for row in cursor.fetchall():
                item = dict(zip(columns, row))
                
                # 해시태그 JSON 파싱
                if item.get('hashtags'):
                    try:
                        item['hashtags'] = json.loads(item['hashtags'])
                    except json.JSONDecodeError:
                        item['hashtags'] = []
                
                results.append(item)
                
            return results
            
        except sqlite3.Error as e:
            self.logger.error(f"카테고리별 북마크 가져오기 실패: {e}")
            return []
            
        finally:
            conn.close()
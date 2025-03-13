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
            url TEXT,
            hashtags TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # image, thumbnail 필드 추가 (이미 존재하는 테이블에 필드를 추가하기 위한 마이그레이션)
        try:
            cursor.execute('ALTER TABLE bookmarks ADD COLUMN thumbnail TEXT')
        except sqlite3.OperationalError:
            # 이미 필드가 존재하는 경우 예외가 발생하므로 무시
            pass
            
        try:
            cursor.execute('ALTER TABLE bookmarks ADD COLUMN image TEXT')
        except sqlite3.OperationalError:
            # 이미 필드가 존재하는 경우 예외가 무시
            pass
        
        # 설정 테이블 생성
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        conn.commit()
        conn.close()
        
    def _get_connection(self) -> sqlite3.Connection:
        """데이터베이스 연결을 반환합니다.
        
        Returns:
            SQLite 데이터베이스 연결 객체
        """
        return sqlite3.connect(self.db_path)
        
    def add_bookmark(self, bookmark_data: Dict[str, Any]) -> int:
        """북마크 데이터를 저장합니다.
        
        Args:
            bookmark_data: 북마크 데이터 딕셔너리
            
        Returns:
            저장된 북마크의 ID
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # 중복 피드 체크
        cursor.execute("SELECT id FROM bookmarks WHERE feed_id = ?", (bookmark_data['feed_id'],))
        existing = cursor.fetchone()
        if existing:
            self.logger.info(f"DB에 저장되어 있는 피드이므로 넘어갑니다. feed_id: {bookmark_data['feed_id']}")
            conn.close()
            return -1  # 이미 존재하는 항목
        
        # 해시태그는 JSON으로 저장
        if 'hashtags' in bookmark_data and isinstance(bookmark_data['hashtags'], list):
            bookmark_data['hashtags'] = json.dumps(bookmark_data['hashtags'], ensure_ascii=False)
        
        try:
            cursor.execute('''
            INSERT INTO bookmarks (collection_id, feed_id, media_type, caption, media_url, thumbnail_url, url, hashtags)
            VALUES (:collection_id, :feed_id, :media_type, :caption, :media_url, :thumbnail_url, :url, :hashtags)
            ''', bookmark_data)
            
            bookmark_id = cursor.lastrowid
            conn.commit()
            self.logger.info(f"북마크 저장됨: ID {bookmark_id}")
            return bookmark_id
            
        except sqlite3.Error as e:
            conn.rollback()
            self.logger.error(f"북마크 저장 실패: {e}")
            st.error(f"북마크 저장 실패: {e}")
            return -1
            
        finally:
            conn.close()

    def add_bookmark_batch(self, bookmarks: List[dict]) -> Tuple[int, int]:
        """북마크 목록을 일괄적으로 추가합니다.
        
        Args:
            bookmarks: 북마크 목록
            
        Returns:
            (성공한 항목 수, 실패한 항목 수) 튜플
        """
        if not bookmarks:
            return (0, 0)
        
        conn = self._get_connection()
        cursor = conn.cursor()
        success_count = 0
        fail_count = 0
        
        try:
            # 트랜잭션 시작
            conn.execute('BEGIN TRANSACTION')
            
            for bookmark in bookmarks:
                try:
                    feed_id = bookmark.get('feed_id')
                    if not feed_id:
                        self.logger.warning("feed_id가 없는 북마크 건너뜀")
                        fail_count += 1
                        continue
                    
                    # 이미 존재하는지 확인
                    cursor.execute("SELECT COUNT(*) FROM bookmarks WHERE feed_id = ?", (feed_id,))
                    if cursor.fetchone()[0] > 0:
                        # 이미 존재하면 스킵
                        pass
                    else:
                        # 해시태그는 JSON으로 저장
                        if 'hashtags' in bookmark and isinstance(bookmark['hashtags'], list):
                            bookmark['hashtags'] = json.dumps(bookmark['hashtags'], ensure_ascii=False)
                        # 새로 추가
                        cursor.execute('''
                        INSERT INTO bookmarks (collection_id, feed_id, media_type, caption, media_url, thumbnail_url, url, hashtags)
                        VALUES (:collection_id, :feed_id, :media_type, :caption, :media_url, :thumbnail_url, :url, :hashtags)
                        ''', bookmark)
                        
                        bookmark_id = cursor.lastrowid
                        conn.commit()
                        self.logger.info(f"북마크 저장됨: ID {bookmark_id}")
                    
                    success_count += 1
                except Exception as e:
                    self.logger.error(f"북마크 일괄 추가 중 오류 발생: {e}")
                    fail_count += 1
            
            # 트랜잭션 커밋
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"북마크 일괄 추가 실패: {e}")
            return (success_count, fail_count)
        
        finally:
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

    # TODO def get_categories():
    
    # def save_setting(self, key: str, value: Any) -> bool:
    #     """설정 값을 저장합니다.
        
    #     Args:
    #         key: 설정 키
    #         value: 설정 값
            
    #     Returns:
    #         저장 성공 여부
    #     """
    #     conn = self._get_connection()
    #     cursor = conn.cursor()
        
    #     # 객체는 JSON으로 변환
    #     if not isinstance(value, (str, int, float, bool, type(None))):
    #         value = json.dumps(value, ensure_ascii=False)
    #     else:
    #         value = str(value)
        
    #     try:
    #         cursor.execute('''
    #         INSERT INTO settings (key, value, updated_at)
    #         VALUES (?, ?, CURRENT_TIMESTAMP)
    #         ON CONFLICT(key) DO UPDATE SET
    #         value = excluded.value,
    #         updated_at = CURRENT_TIMESTAMP
    #         ''', (key, value))
            
    #         conn.commit()
    #         self.logger.info(f"설정 저장됨: {key}")
    #         return True
            
    #     except sqlite3.Error as e:
    #         conn.rollback()
    #         self.logger.error(f"설정 저장 실패: {key}, {e}")
    #         return False
            
    #     finally:
    #         conn.close()
    
    # def get_setting(self, key: str, default: Any = None) -> Any:
    #     """설정 값을 가져옵니다.
        
    #     Args:
    #         key: 설정 키
    #         default: 기본 반환 값
            
    #     Returns:
    #         설정 값 또는 기본값
    #     """
    #     conn = self._get_connection()
    #     cursor = conn.cursor()
        
    #     try:
    #         cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    #         result = cursor.fetchone()
            
    #         if result:
    #             value = result[0]
                
    #             # JSON 형식인지 확인하여 파싱
    #             if value and (value.startswith('{') or value.startswith('[')):
    #                 try:
    #                     return json.loads(value)
    #                 except json.JSONDecodeError:
    #                     pass
                
    #             return value
            
    #         return default
            
    #     except sqlite3.Error as e:
    #         self.logger.error(f"설정 가져오기 실패: {key}, {e}")
    #         return default
            
    #     finally:
    #         conn.close()
    
    # def export_bookmarks_to_json(self, output_file: str) -> bool:
    #     """북마크를 JSON 파일로 내보냅니다.
        
    #     Args:
    #         output_file: 저장할 파일 경로
            
    #     Returns:
    #         내보내기 성공 여부
    #     """
    #     try:
    #         bookmarks = self.get_bookmarks(limit=10000)  # 충분히 큰 제한값
            
    #         with open(output_file, 'w', encoding='utf-8') as f:
    #             json.dump(bookmarks, f, ensure_ascii=False, indent=4)
                
    #         self.logger.info(f"{len(bookmarks)}개 북마크를 {output_file}로 내보냈습니다.")
    #         return True
            
    #     except Exception as e:
    #         self.logger.error(f"북마크 내보내기 실패: {e}")
    #         return False
    
    # def import_bookmarks_from_json(self, input_file: str) -> Tuple[int, int]:
    #     """JSON 파일에서 북마크를 가져옵니다.
        
    #     Args:
    #         input_file: 가져올 파일 경로
            
    #     Returns:
    #         (성공한 항목 수, 실패한 항목 수) 튜플
    #     """
    #     if not os.path.exists(input_file):
    #         self.logger.error(f"파일을 찾을 수 없음: {input_file}")
    #         return (0, 0)
            
    #     try:
    #         with open(input_file, 'r', encoding='utf-8') as f:
    #             bookmarks = json.load(f)
                
    #         if not isinstance(bookmarks, list):
    #             self.logger.error(f"유효하지 않은 북마크 데이터 형식: {input_file}")
    #             return (0, 0)
            
    #         success_count = 0
    #         fail_count = 0
            
    #         for bookmark in bookmarks:
    #             # 기존 ID 필드 제거 (충돌 방지)
    #             if 'id' in bookmark:
    #                 del bookmark['id']
                
    #             # created_at 필드 제거 (DB에서 자동 생성)
    #             if 'created_at' in bookmark:
    #                 del bookmark['created_at']
                
    #             if self.add_bookmark(bookmark) > 0:
    #                 success_count += 1
    #             else:
    #                 fail_count += 1
                    
    #         self.logger.info(f"북마크 가져오기 완료: {success_count}개 성공, {fail_count}개 실패")
    #         return (success_count, fail_count)
            
    #     except Exception as e:
    #         self.logger.error(f"북마크 가져오기 실패: {e}")
    #         return (0, 0)
import os
import json
from pathlib import Path
import numpy as np
import faiss
import sqlite3
from langchain_openai import AzureOpenAIEmbeddings
from dotenv import load_dotenv
import streamlit as st
import traceback

# .env 파일에서 환경 변수 로드
load_dotenv()

# FAISS 벡터 스토어 초기화
# 임베딩 설정
embeddings = AzureOpenAIEmbeddings(
    model=os.getenv("AOAI_DEPLOY_EMBED_ADA"),
    openai_api_version="2024-02-01",
    api_key=os.getenv("AOAI_API_KEY"),
    azure_endpoint=os.getenv("AOAI_ENDPOINT"),
)

class VectorStore:
    """FAISS를 이용한 벡터 검색 클래스"""
    def __init__(self, db_path):
        self.db_path = db_path
        
        # Azure OpenAI Embeddings 설정
        self.embeddings = embeddings
        
        # FAISS 인덱스 생성 또는 로드
        self.index_path = Path(db_path).parent / "faiss_index"
        self.index_path.mkdir(exist_ok=True)
        self.index_file = self.index_path / "bookmark_vectors.index"
        self.mapping_file = self.index_path / "id_mapping.json"
        
        self._load_or_create_index()
    
    def _load_or_create_index(self):
        """FAISS 인덱스 로드 또는 생성"""
        # 예시 임베딩 생성해서 차원 확인
        sample_vector = self.embeddings.embed_query("sample text")
        self.dimension = len(sample_vector)
        
        # ID 매핑 로드 또는 생성
        if self.mapping_file.exists():
            with open(self.mapping_file, 'r') as f:
                self.id_to_index = json.load(f)
        else:
            self.id_to_index = {}
        
        # 역방향 인덱스 -> ID 매핑 생성
        self.index_to_id = {v: k for k, v in self.id_to_index.items()}
        
        # FAISS 인덱스 로드 또는 생성
        if self.index_file.exists():
            self.index = faiss.read_index(str(self.index_file))
        else:
            self.index = faiss.IndexFlatIP(self.dimension)  # 내적 유사도 사용 (코사인 유사도와 동일 효과)
            
        # print(f"FAISS 인덱스 준비 완료: {self.index.ntotal} 벡터, {self.dimension} 차원")
    
    def _save_index(self):
        """FAISS 인덱스와 매핑 저장"""
        faiss.write_index(self.index, str(self.index_file))
        with open(self.mapping_file, 'w') as f:
            json.dump(self.id_to_index, f)
    
    def add_bookmark(self, bookmark):
        """북마크 벡터 추가"""
        try:
            if not bookmark.get('caption'):
                return
            
            bookmark_id = bookmark['feed_id']
            text = bookmark['caption']
            
            # Azure OpenAI API로 벡터 생성
            vector = self.embeddings.embed_query(text)
            vector_np = np.array([vector]).astype('float32')
            
            # 북마크 ID가 이미 있는지 확인
            if bookmark_id in self.id_to_index:
                # 기존 벡터 삭제
                old_index = self.id_to_index[bookmark_id]
                # FAISS는 벡터를 직접 삭제할 수 없어서, 여기서는 업데이트로 처리
                # 실제 프로덕션에서는 더 복잡한 로직이 필요할 수 있음
            
            # 새 벡터 추가
            self.index.add(vector_np)
            new_idx = self.index.ntotal - 1
            
            # 매핑 업데이트
            self.id_to_index[bookmark_id] = new_idx
            self.index_to_id[new_idx] = bookmark_id
            
            # 인덱스 저장
            self._save_index()
            
        except Exception as e:
            print(f"북마크 벡터 추가 중 오류: {e}")
            st.error(f"북마크 벡터 추가 중 오류: {e}")
            return False
        
    def add_bookmark_batch(self, bookmarks):
        """북마크 벡터를 일괄 추가"""
        try:
            # 벡터가 있는 유효한 북마크만 필터링
            valid_bookmarks = [b for b in bookmarks if b.get('caption')]
            
            if not valid_bookmarks:
                print("캡션이 있는 유효한 북마크가 없습니다.")
                return True
            
            # 모든 유효 북마크에 대한 임베딩 한번에 생성
            texts = [bookmark['caption'] for bookmark in valid_bookmarks]
            
            # 임베딩 생성 (텍스트당 하나씩)
            vectors = []
            try:
                for i, text in enumerate(texts):
                    try:
                        vector = self.embeddings.embed_query(text)
                        vectors.append(vector)
                    except Exception as embed_error:
                        # 개별 임베딩 오류 처리
                        bookmark_id = valid_bookmarks[i]['feed_id']
                        print(f"북마크 {bookmark_id}의 임베딩 생성 중 오류: {embed_error}")
                        # 해당 북마크만 건너뛰고 계속 진행
                        continue
            except Exception as batch_error:
                # 전체 임베딩 프로세스 실패 시
                error_msg = f"임베딩 생성 중 일괄 오류: {batch_error}"
                print(error_msg)
                if 'st' in globals() and hasattr(st, 'error'):
                    st.error(error_msg)
                return False
            
            if not vectors:
                print("생성된 유효한 벡터가 없습니다.")
                return True
                
            # 벡터 배열로 변환
            vectors_np = np.array(vectors).astype('float32')
            
            # 시작 인덱스 저장
            start_idx = self.index.ntotal
            
            # FAISS에 벡터 일괄 추가
            try:
                self.index.add(vectors_np)
            except Exception as faiss_error:
                error_msg = f"FAISS 인덱스에 벡터 추가 중 오류: {faiss_error}"
                print(error_msg)
                if 'st' in globals() and hasattr(st, 'error'):
                    st.error(error_msg)
                return False
            
            # 매핑 업데이트
            update_count = 0
            for i, bookmark in enumerate(valid_bookmarks):
                if i >= len(vectors):
                    continue  # 임베딩 생성에 실패한 북마크는 건너뜀
                    
                bookmark_id = bookmark['feed_id']
                new_idx = start_idx + i
                
                # 기존 매핑이 있었다면 제거
                if bookmark_id in self.id_to_index:
                    old_idx = self.id_to_index[bookmark_id]
                    if old_idx in self.index_to_id:
                        del self.index_to_id[old_idx]
                
                # 새 매핑 추가
                self.id_to_index[bookmark_id] = new_idx
                self.index_to_id[new_idx] = bookmark_id
                update_count += 1
            
            # 인덱스 저장
            try:
                self._save_index()
                print(f"북마크 벡터 {update_count}개를 성공적으로 추가했습니다.")
                return True
            except Exception as save_error:
                error_msg = f"인덱스 저장 중 오류: {save_error}"
                print(error_msg)
                if 'st' in globals() and hasattr(st, 'error'):
                    st.error(error_msg)
                return False
                
        except Exception as e:
            error_msg = f"북마크 벡터 일괄 추가 중 예상치 못한 오류: {e}"
            print(error_msg)
            # Streamlit이 사용 가능할 때만 UI 오류 표시
            if 'st' in globals() and hasattr(st, 'error'):
                st.error(error_msg)
            return False

    def search_bookmarks(self, query, limit=10):
        """검색어와 유사한 북마크 찾기"""
        try:
            # 북마크가 없으면 빈 리스트 반환
            if self.index.ntotal == 0:
                print("벡터 인덱스가 비어 있습니다")
                return []
            
            # 쿼리 벡터 생성
            query_vector = self.embeddings.embed_query(query)
            query_vector_np = np.array([query_vector]).astype('float32')

            # 쿼리 벡터 정규화 (코사인 유사도를 위해)
            faiss.normalize_L2(query_vector_np)
            
            # FAISS로 유사 벡터 검색
            k = min(limit, self.index.ntotal)  # k는 인덱스 크기를 초과할 수 없음
            distances, indices = self.index.search(query_vector_np, k)
            
            print(f"검색 결과: {len(indices[0])}개 항목 발견, 유사도: {distances[0]}")
            
            # 검색 결과에서 북마크 ID 추출
            bookmark_ids = []
            missing_indices = []
            for idx in indices[0]:
                idx_int = int(idx)
                bookmark_id = self.index_to_id.get(idx_int)
                if bookmark_id:
                    bookmark_ids.append(bookmark_id)
                else:
                    missing_indices.append(idx_int)
                    print(f"경고: 인덱스 {idx_int}에 대한 북마크 ID를 찾을 수 없습니다")
            
            # 누락된 인덱스가 많을 경우 인덱스 재구축 권장
            if missing_indices and len(missing_indices) > len(indices[0]) / 2:
                print(f"경고: {len(missing_indices)}개의 인덱스가 매핑에 없습니다. 인덱스 재구축을 권장합니다.")
                print("rebuild_index() 메서드를 실행하여 인덱스를 재구축하세요.")
            
            if not bookmark_ids:
                print("유효한 북마크 ID를 찾을 수 없습니다")
                return []
                
            # 북마크 정보 가져오기
            bookmarks = []
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    for bookmark_id in bookmark_ids:
                        cursor.execute("SELECT * FROM bookmarks WHERE feed_id = ?", (bookmark_id,))
                        result = cursor.fetchone()
                        if result:
                            # 컬럼 이름 가져오기
                            columns = [desc[0] for desc in cursor.description]
                            # 딕셔너리로 변환
                            bookmark = dict(zip(columns, result))
                            
                            # 해시태그 JSON 파싱
                            if bookmark.get('hashtags'):
                                try:
                                    bookmark['hashtags'] = json.loads(bookmark['hashtags'])
                                except json.JSONDecodeError:
                                    bookmark['hashtags'] = []
                            
                            bookmarks.append(bookmark)
                        else:
                            print(f"북마크 ID {bookmark_id}를 DB에서 찾을 수 없습니다")
            except sqlite3.Error as db_error:
                print(f"데이터베이스 오류: {db_error}")
                
            print(f"총 {len(bookmarks)}개의 북마크를 검색 결과로 반환합니다")
            return bookmarks
                
        except Exception as e:
            print(f"북마크 검색 중 오류: {e}")
            import traceback
            traceback.print_exc()  # 자세한 오류 추적
            return []
    
    def delete_bookmark(self, bookmark_id):
        """북마크 벡터 삭제"""
        try:
            if bookmark_id in self.id_to_index:
                # FAISS는 직접적인 삭제를 지원하지 않아 인덱스를 재구성해야 함
                # 실제 구현에서는 더 효율적인 방법을 사용해야 함
                # 여기서는 ID 매핑에서만 제거하는 간단한 방식 사용
                idx = self.id_to_index[bookmark_id]
                del self.id_to_index[bookmark_id]
                if idx in self.index_to_id:
                    del self.index_to_id[idx]
                
                print(f"주의: 북마크 ID {bookmark_id}를 매핑에서 제거했지만, 벡터는 FAISS 인덱스에 남아있습니다.")
                print("다수의 북마크를 삭제한 경우 rebuild_index()를 호출하는 것이 좋습니다.")
                
                # 인덱스 저장
                self._save_index()
                return True
            return False
        except Exception as e:
            print(f"북마크 벡터 삭제 중 오류: {e}")
            return False
    
    def rebuild_index(self):
        """인덱스 완전히 재구축 (대규모 삭제 후 필요할 수 있음)"""
        try:
            print("FAISS 인덱스와 ID 매핑을 재구축합니다...")
            # 기존 북마크 데이터 가져오기
            bookmarks = []
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM bookmarks")
                columns = [desc[0] for desc in cursor.description]
                
                for row in cursor.fetchall():
                    # 딕셔너리로 변환
                    bookmark = dict(zip(columns, row))
                    
                    # 해시태그 JSON 파싱
                    if bookmark.get('hashtags'):
                        try:
                            bookmark['hashtags'] = json.loads(bookmark['hashtags'])
                        except json.JSONDecodeError:
                            bookmark['hashtags'] = []
                            
                    bookmarks.append(bookmark)
            
            # 새 인덱스 생성
            self.index = faiss.IndexFlatIP(self.dimension)  # 내적 유사도 사용
            self.id_to_index = {}
            self.index_to_id = {}
            
            print(f"총 {len(bookmarks)}개의 북마크에 대해 새 인덱스를 생성합니다...")
            
            # 모든 북마크 다시 추가
            added_count = 0
            for bookmark in bookmarks:
                if bookmark.get('caption'):
                    bookmark_id = bookmark['feed_id']
                    vector = self.embeddings.embed_query(bookmark['caption'])
                    vector_np = np.array([vector]).astype('float32')
                    
                    # 새 벡터 추가
                    self.index.add(vector_np)
                    new_idx = self.index.ntotal - 1
                    
                    # 매핑 업데이트
                    self.id_to_index[bookmark_id] = new_idx
                    self.index_to_id[new_idx] = bookmark_id
                    added_count += 1
            
            # 인덱스 저장
            self._save_index()
            print(f"인덱스 재구축 완료: {added_count}개 북마크 벡터 추가됨")
            return True
        except Exception as e:
            print(f"인덱스 재구축 중 오류: {e}")
            traceback.print_exc()  # 자세한 오류 추적
            return False
            
    def check_index_health(self):
        """인덱스 상태 확인 및 진단"""
        try:
            total_vectors = self.index.ntotal
            total_mappings = len(self.id_to_index)
            
            print(f"== FAISS 인덱스 상태 ==")
            print(f"벡터 수: {total_vectors}")
            print(f"ID 매핑 수: {total_mappings}")
            
            # 불일치 확인
            if total_vectors != total_mappings:
                print(f"경고: 벡터 수와 매핑 수가 일치하지 않습니다 ({total_vectors} vs {total_mappings})")
                print("rebuild_index()를 실행하여 인덱스를 재구축하는 것을 권장합니다.")
            else:
                print("인덱스 상태가 양호합니다.")
                
            return {
                "total_vectors": total_vectors,
                "total_mappings": total_mappings,
                "is_healthy": total_vectors == total_mappings
            }
        except Exception as e:
            print(f"인덱스 상태 확인 중 오류: {e}")
            return {"error": str(e)}
# NOTE 사외망에서만 사용 가능
import os
import sys
import base64
import requests
from pathlib import Path
from typing import List
import logging
import json
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.append(project_root)
from db import BookmarkDatabase

logger = logging.getLogger(__name__)

def download_thumbnails_js(keyword, image_dir: str = "./data/image") -> List[str]:
    """북마크의 썸네일 이미지를 다운로드합니다.
    
    Args:
        db: 데이터베이스 인스턴스
        image_dir: 이미지 저장 디렉토리
        
    Returns:
        성공적으로 다운로드된 feed_id 목록
    """
    json_path = f"./data/{keyword}.json"

    # 이미지 디렉토리 생성
    image_dir = f"{image_dir}/{keyword}"
    os.makedirs(image_dir, exist_ok=True)
    
    # json에서 feed_id와 thumbnail_url 가져오기
    results = []

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # feed_id와 thumbnail_url만 추출
    results = []
    for item in data:
        feed_id = item.get('feed_id')
        thumbnail_url = item.get('thumbnail_url')
        
        # 둘 다 값이 있는 경우만 추가
        if feed_id and thumbnail_url:
            results.append((feed_id, thumbnail_url))
    
    success_feed_ids = []
    
    for feed_id, thumbnail_url in results:
        try:
            # 이미지 다운로드
            response = requests.get(thumbnail_url)
            response.raise_for_status()
            
            # 이미지 저장
            image_path = os.path.join(image_dir, f"{feed_id}.png")
            with open(image_path, "wb") as f:
                f.write(response.content)
            
            success_feed_ids.append(feed_id)
            logger.info(f"썸네일 다운로드 성공: {feed_id}")
            
        except Exception as e:
            logger.error(f"썸네일 다운로드 실패 ({feed_id}): {str(e)}")
            continue
    
    return success_feed_ids

def download_thumbnails_db(db: BookmarkDatabase, image_dir: str = "./data/image") -> List[str]:
    """북마크의 썸네일 이미지를 다운로드합니다.
    
    Args:
        db: 데이터베이스 인스턴스
        image_dir: 이미지 저장 디렉토리
        
    Returns:
        성공적으로 다운로드된 feed_id 목록
    """
    # 이미지 디렉토리 생성
    os.makedirs(image_dir, exist_ok=True)
    
    # feed_id와 thumbnail_url 가져오기
    conn = db._get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT feed_id, thumbnail_url FROM bookmarks WHERE thumbnail_url IS NOT NULL")
    results = cursor.fetchall()
    conn.close()
    
    success_feed_ids = []
    
    for feed_id, thumbnail_url in results:
        try:
            # 이미지 다운로드
            response = requests.get(thumbnail_url)
            response.raise_for_status()
            
            # 이미지 저장
            image_path = os.path.join(image_dir, f"{feed_id}.png")
            with open(image_path, "wb") as f:
                f.write(response.content)
            
            success_feed_ids.append(feed_id)
            logger.info(f"썸네일 다운로드 성공: {feed_id}")
            
        except Exception as e:
            logger.error(f"썸네일 다운로드 실패 ({feed_id}): {str(e)}")
            continue
    
    return success_feed_ids

def update_thumbnails_in_db(db: BookmarkDatabase, image_dir: str = "./data/image") -> None:
    """다운로드된 썸네일을 base64로 인코딩하여 DB에 저장합니다.
    
    Args:
        db: 데이터베이스 인스턴스
        image_dir: 이미지 저장 디렉토리
    """
    conn = db._get_connection()
    cursor = conn.cursor()
    
    try:
        # 이미지 파일 목록 가져오기
        image_files = [f for f in os.listdir(image_dir) if f.endswith('.png')]
        
        # 각 이미지 파일 처리
        for image_file in image_files:
            feed_id = image_file.replace('.png', '')
            image_path = os.path.join(image_dir, image_file)
            
            try:
                # 이미지를 base64로 인코딩
                with open(image_path, "rb") as f:
                    image_data = f.read()
                    base64_data = base64.b64encode(image_data).decode('utf-8')
                
                # DB 업데이트
                cursor.execute(
                    "UPDATE bookmarks SET thumbnail = ? WHERE feed_id = ?",
                    (base64_data, feed_id)
                )
                
                logger.info(f"썸네일 DB 업데이트 성공: {feed_id}")
                
            except Exception as e:
                logger.error(f"썸네일 DB 업데이트 실패 ({feed_id}): {str(e)}")
                continue
        
        conn.commit()
        
    except Exception as e:
        conn.rollback()
        logger.error(f"DB 업데이트 중 오류 발생: {str(e)}")
        
    finally:
        conn.close()

def main():
    """메인 실행 함수"""
    # 데이터베이스 초기화
    db = BookmarkDatabase("./data/bookmarks.db")
    keyword = "뮤지컬"
    
    # 썸네일 다운로드
    print("썸네일 다운로드 시작...")
    # success_feed_ids = download_thumbnails_db(db)
    success_feed_ids = download_thumbnails_js(keyword)
    print(f"썸네일 다운로드 완료: {len(success_feed_ids)}개 성공")
    
    # # DB 업데이트
    # print("DB 업데이트 시작...")
    # update_thumbnails_in_db(db)
    # print("DB 업데이트 완료")

if __name__ == "__main__":
    main() 
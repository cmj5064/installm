import os
import re
import logging
import hashlib
import io
from PIL import Image
import requests
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from typing import Dict, Any
import datetime

# 로깅 설정
logger = logging.basicConfig(
    filename='bookmarks.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def log_error(message: str) -> None:
    """오류 로깅 함수"""
    logging.error(message)
    print(f"오류: {message}")

def extract_text_from_url(url: str) -> str:
    """URL에서 텍스트 추출"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 불필요한 태그 제거
        for tag in soup(['script', 'style', 'meta', 'noscript']):
            tag.decompose()
        
        # 텍스트 추출 및 정리
        text = soup.get_text(separator=' ', strip=True)
        
        # 텍스트 길이 제한 (너무 길면 임베딩 처리시 문제 발생)
        max_length = 3000
        if len(text) > max_length:
            text = text[:max_length] + "..."
        
        return text
    except Exception as e:
        log_error(f"URL 텍스트 추출 중 오류: {e}")
        return ""

def create_opengraph_preview(url: str) -> Dict[str, Any]:
    """URL에서 OpenGraph 메타데이터 추출"""
    result = {
        "title": "",
        "description": "",
        "image": ""
    }
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # OpenGraph 태그 찾기
        og_title = soup.find("meta", property="og:title")
        og_desc = soup.find("meta", property="og:description")
        og_image = soup.find("meta", property="og:image")
        
        # OpenGraph 태그가 없으면 일반 태그 사용
        title = og_title["content"] if og_title else soup.title.string if soup.title else url
        description = og_desc["content"] if og_desc else ""
        image = og_image["content"] if og_image else ""
        
        result["title"] = title
        result["description"] = description
        result["image"] = image
        
        return result
    except Exception as e:
        log_error(f"OpenGraph 메타데이터 추출 중 오류: {e}")
        return result

def log_info(message):
    """정보 메시지를 로깅합니다.
    
    Args:
        message: 로깅할 정보 메시지
    """
    logger.info(message)

def is_valid_url(url):
    """URL이 유효한지 확인합니다.
    
    Args:
        url: 확인할 URL 문자열
        
    Returns:
        유효한 URL이면 True, 아니면 False
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def download_image(url, max_retries=3):
    """URL에서 이미지를 다운로드합니다.
    
    Args:
        url: 이미지 URL
        max_retries: 최대 재시도 횟수
        
    Returns:
        PIL Image 객체 또는 None
    """
    if not is_valid_url(url):
        return None
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return Image.open(io.BytesIO(response.content))
        except Exception as e:
            if attempt == max_retries - 1:  # 마지막 시도라면
                print(f"이미지 다운로드 실패: {url}, 오류: {e}")
    
    return None

def sanitize_filename(filename):
    """파일 이름에서 유효하지 않은 문자를 제거합니다.
    
    Args:
        filename: 정리할 파일 이름
        
    Returns:
        정리된 파일 이름
    """
    # 유효하지 않은 문자 제거
    invalid_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(invalid_chars, '', filename)
    
    # 앞뒤 공백 제거하고 길이 제한
    sanitized = sanitized.strip()
    if len(sanitized) > 200:
        sanitized = sanitized[:200]
    
    # 비어있으면 기본값 사용
    if not sanitized:
        sanitized = "unnamed_file"
    
    return sanitized

def ensure_dir(directory):
    """디렉토리가 존재하는지 확인하고, 없으면 생성합니다.
    
    Args:
        directory: 확인할 디렉토리 경로
    """
    if not os.path.exists(directory):
        os.makedirs(directory)

def generate_thumbnail(image, max_size=(200, 200)):
    """이미지의 섬네일을 생성합니다.
    
    Args:
        image: PIL 이미지 객체
        max_size: 최대 섬네일 크기 (너비, 높이)
        
    Returns:
        섬네일 이미지
    """
    if not image:
        return None
    
    # 원본 비율 유지하면서 축소
    image.thumbnail(max_size, Image.LANCZOS)
    return image

def format_datetime(dt_str, input_format=None, output_format="%Y-%m-%d %H:%M"):
    """날짜/시간 문자열의 형식을 변환합니다.
    
    Args:
        dt_str: 변환할 날짜/시간 문자열
        input_format: 입력 형식 (None이면 자동 감지 시도)
        output_format: 출력 형식
        
    Returns:
        변환된 날짜/시간 문자열 또는 원본 문자열
    """
    if not dt_str:
        return ""
    
    # Unix 타임스탬프 처리
    if isinstance(dt_str, (int, float)) or dt_str.isdigit():
        timestamp = float(dt_str)
        return datetime.datetime.fromtimestamp(timestamp).strftime(output_format)
    
    # 형식이 제공된 경우
    if input_format:
        try:
            dt = datetime.datetime.strptime(dt_str, input_format)
            return dt.strftime(output_format)
        except ValueError:
            pass
    
    # 일반적인 형식들 시도
    common_formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y"
    ]
    
    for fmt in common_formats:
        try:
            dt = datetime.datetime.strptime(dt_str, fmt)
            return dt.strftime(output_format)
        except ValueError:
            continue
    
    # 변환 실패 시 원본 반환
    return dt_str

def get_text_hash(text):
    """텍스트의 해시값을 생성합니다.
    
    Args:
        text: 해시할 텍스트
        
    Returns:
        텍스트의 SHA-256 해시값
    """
    if not text:
        return None
    
    # 텍스트가 바이트가 아니면 인코딩
    if isinstance(text, str):
        text = text.encode('utf-8')
    
    return hashlib.sha256(text).hexdigest()

def truncate_text(text, max_length=100, ellipsis="..."):
    """텍스트를 최대 길이로 자릅니다.
    
    Args:
        text: 자를 텍스트
        max_length: 최대 길이
        ellipsis: 생략 부호
        
    Returns:
        잘린 텍스트
    """
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(ellipsis)] + ellipsis
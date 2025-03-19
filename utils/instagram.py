# import json
import codecs
import os
import logging
import datetime
from typing import Dict, List, Optional
import re
import requests

try:
    from instagram_private_api import (
        Client,
        ClientError,
        ClientLoginError,
        ClientCookieExpiredError,
        ClientLoginRequiredError,
    )
except ImportError:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
    from instagram_private_api import (
        Client,
        ClientError,
        ClientLoginError,
        ClientCookieExpiredError,
        ClientLoginRequiredError,
    )


class InstagramClient:
    """인스타그램 API 클라이언트 클래스"""
    
    # def __init__(self, username: str, password: str, settings_file: str = "credentials.json"):
    def __init__(self, username: str, password: str):
        """인스타그램 API 클라이언트를 초기화합니다.
        
        Args:
            username: 인스타그램 사용자명
            password: 인스타그램 비밀번호
            settings_file: 인증 정보를 저장할 파일 경로
        """
        self.logger = logging.getLogger("instagram")
        self.username = username
        self.password = password
        # self.settings_file = settings_file
        self.client = None
        self._login()
    
    def _to_json(self, python_object):
        """파이썬 객체를 JSON으로 직렬화합니다."""
        if isinstance(python_object, bytes):
            return {
                "__class__": "bytes",
                "__value__": codecs.encode(python_object, "base64").decode(),
            }
        raise TypeError(repr(python_object) + " is not JSON serializable")
    
    def _from_json(self, json_object):
        """JSON 객체를 파이썬 객체로 역직렬화합니다."""
        if "__class__" in json_object and json_object["__class__"] == "bytes":
            return codecs.decode(json_object["__value__"].encode(), "base64")
        return json_object
    
    # def _onlogin_callback(self, api):
    #     """로그인 성공 후 콜백 함수입니다."""
    #     cache_settings = api.settings
    #     with open(self.settings_file, "w") as outfile:
    #         json.dump(cache_settings, outfile, default=self._to_json)
    #         self.logger.info(f"인증 정보 저장 완료: {self.settings_file}")
    
    def _login(self):
        """인스타그램에 로그인합니다."""
        device_id = None
        try:
            # if not os.path.isfile(self.settings_file):
            #     # 설정 파일이 없는 경우 새로 로그인
            #     self.logger.info(f"인증 정보 파일을 찾을 수 없음: {self.settings_file}")
            #     self.client = Client(
            #         self.username,
            #         self.password,
            #         on_login=lambda x: self._onlogin_callback(x)
            #     )
            # else:
            #     # 기존 설정 파일 사용
            #     with open(self.settings_file) as file_data:
            #         cached_settings = json.load(file_data, object_hook=self._from_json)
            #     self.logger.info(f"기존 인증 정보 재사용: {self.settings_file}")
                
            #     device_id = cached_settings.get("device_id")
            #     # 인증 설정 재사용
            #     self.client = Client(
            #         self.username,
            #         self.password,
            #         settings=cached_settings
            #     )
            self.client = Client(
                self.username,
                self.password,
                # on_login=lambda x: self._onlogin_callback(x)
            )
                
        except (ClientCookieExpiredError, ClientLoginRequiredError) as e:
            # self.logger.warning(f"쿠키 만료/로그인 필요: {e}")
            self.logger.warning(f"로그인 실패: {e}")
            
            # 만료된 로그인 정보, 재로그인 시도
            self.client = Client(
                self.username,
                self.password,
                device_id=device_id,
                # on_login=lambda x: self._onlogin_callback(x)
            )
            
        except ClientLoginError as e:
            self.logger.error(f"로그인 에러: {e}")
            raise
            
        except ClientError as e:
            self.logger.error(f"클라이언트 에러 {e.msg} (코드: {e.code}, 응답: {e.error_response})")
            raise
            
        except Exception as e:
            self.logger.error(f"예상치 못한 에러: {e}")
            raise
        
        # 로그인 만료 시간 출력
        cookie_expiry = self.client.cookie_jar.auth_expires
        expire_time = datetime.datetime.fromtimestamp(cookie_expiry).strftime("%Y-%m-%dT%H:%M:%SZ")
        # self.logger.info(f"인증 정보 만료: {expire_time}")
    
    def get_saved_feed(self, collection_id: str = 'all-posts') -> List[Dict]:
        """사용자의 저장된 포스트를 가져옵니다.
        
        Args:
            collection_id: 가져올 컬렉션 ID (기본값: 'all-posts'는 모든 저장된 포스트)
            
        Returns:
            저장된 포스트 목록
        """
        self.logger.info(f"저장된 피드 가져오기: 컬렉션 {collection_id}")
        
        saved_collection = []
        
        try:
            # 첫 번째 페이지 가져오기
            results = self.client.saved_feed()
            saved_collection.extend(results.get('items', []))
            
            # 다음 페이지가 있으면 모두 가져오기
            next_max_id = results.get('next_max_id')
            while next_max_id:
                self.logger.debug(f"다음 페이지 가져오기: max_id={next_max_id}")
                results = self.client.saved_feed(max_id=next_max_id)
                saved_collection.extend(results.get('items', []))
                next_max_id = results.get('next_max_id')
            
            # 컬렉션 필터링 및 정규화
            filtered_posts = []
            for item in saved_collection:
                media = item.get('media', {})
                # 특정 컬렉션 ID의 포스트만 필터링
                if collection_id == 'all-posts' or collection_id in media.get('saved_collection_ids', []):
                    # 미디어 정보 정규화
                    normalized_media = self.normalize_media_info(media)
                    filtered_posts.append(normalized_media)
            
            self.logger.info(f"저장된 포스트 {len(filtered_posts)}개를 가져왔습니다.")
            # self.logger.info(f"이 중 최근 50개의 포스트를 저장합니다.") # TODO 50개 hardcoding 수정
            return filtered_posts
            
        except Exception as e:
            self.logger.error(f"저장된 피드 가져오기 실패: {e}")
            return []

    # def save_feed_to_file(self, collection_id: str, output_file: str) -> bool:
    #     """저장된 피드를 파일로 저장합니다.
        
    #     Args:
    #         collection_id: 가져올 컬렉션 ID
    #         output_file: 저장할 파일 경로 (.json)
            
    #     Returns:
    #         저장 성공 여부
    #     """
    #     self.logger.info(f"저장된 피드를 {output_file}에 저장합니다.")
        
    #     try:
    #         # 저장된 피드 가져오기
    #         items = self.get_saved_feed(collection_id)
            
    #         # 데이터 포맷팅 (선택적)
    #         formatted_items = []
    #         for idx, item in enumerate(items, 1):
    #             location = item.get('location', {})
    #             formatted = {
    #                 "#": idx,
    #                 "collection_id": collection_id,
    #                 "link": f"https://www.instagram.com/p/{item.get('code')}",
    #                 "location_name": location.get('name', ''),
    #                 "location_map_link": self._create_map_link(location.get('lat'), location.get('lng')),
    #                 "media_type": item.get('media_type_name', ''),
    #                 "caption": item.get('caption_text', '')
    #             }
    #             formatted_items.append(formatted)
            
    #         # JSON 파일로 저장
    #         with open(output_file, 'w', encoding='utf-8') as f:
    #             json.dump(formatted_items, f, ensure_ascii=False, indent=4)
                
    #         self.logger.info(f"{len(formatted_items)}개 항목이 {output_file}에 저장되었습니다.")
    #         return True
            
    #     except Exception as e:
    #         self.logger.error(f"저장된 피드를 파일로 저장하는 중 오류 발생: {e}")
    #         return False

    def _create_map_link(self, lat, lng) -> str:
        """좌표로부터 구글 지도 링크를 생성합니다.
        
        Args:
            lat: 위도
            lng: 경도
            
        Returns:
            구글 지도 링크
        """
        if lat and lng:
            return f'https://www.google.com/maps?q={lat},{lng}'
        return ''

    def extract_media_id_from_url(self, url: str) -> Optional[str]:
        """URL에서 미디어 ID를 추출합니다.
        
        Args:
            url: 인스타그램 포스트 URL
            
        Returns:
            미디어 ID 또는 None
        """
        if not url:
            return None
        
        # URL에서 코드 추출
        shortcode_pattern = r'instagram\.com/p/([^/?]+)'
        match = re.search(shortcode_pattern, url)
        
        if match:
            shortcode = match.group(1)
            try:
                # shortcode를 media_id로 변환
                return self.client.media_id(shortcode)
            except Exception as e:
                self.logger.error(f"미디어 ID 추출 실패: {e}")
        
        return None
    
    # def get_media_info_by_url(self, url: str) -> Optional[Dict]:
    #     """URL로부터 미디어 정보를 가져옵니다.
        
    #     Args:
    #         url: 인스타그램 포스트 URL
            
    #     Returns:
    #         정규화된 미디어 정보 또는 None
    #     """
    #     media_id = self.extract_media_id_from_url(url)
    #     if not media_id:
    #         self.logger.error(f"유효한 인스타그램 URL이 아닙니다: {url}")
    #         return None
        
    #     try:
    #         # 미디어 정보 가져오기
    #         media_info = self.client.media_info(media_id)
            
    #         if 'items' in media_info and media_info['items']:
    #             # 정규화된 형태로 변환
    #             return self.normalize_media_info(media_info['items'][0])
    #         return None
    #     except Exception as e:
    #         self.logger.error(f"미디어 정보 가져오기 실패: {e}")
    #         return None
    
    # def get_user_medias(self, username: str, amount: int = 20) -> List[Dict]:
    #     """사용자의 미디어 목록을 가져옵니다.
        
    #     Args:
    #         username: 인스타그램 사용자명
    #         amount: 가져올 미디어 수
            
    #     Returns:
    #         정규화된 미디어 목록
    #     """
    #     try:
    #         # 사용자 ID 가져오기
    #         user_info = self.client.username_info(username)
    #         user_id = user_info['user']['pk']
            
    #         # 사용자 미디어 가져오기
    #         medias = []
    #         results = self.client.user_feed(user_id)
    #         medias.extend(results.get('items', []))
            
    #         next_max_id = results.get('next_max_id')
            
    #         # 요청한 수만큼 가져오기
    #         while next_max_id and len(medias) < amount:
    #             results = self.client.user_feed(user_id, max_id=next_max_id)
    #             medias.extend(results.get('items', []))
    #             next_max_id = results.get('next_max_id')
                
    #             # 속도 제한 방지를 위한 대기
    #             time.sleep(1)
            
    #         # 최대 amount 개수만큼 제한
    #         medias = medias[:amount]
            
    #         # 각 미디어 정보 정규화
    #         normalized_medias = []
    #         for media in medias:
    #             normalized = self.normalize_media_info(media)
    #             if normalized:
    #                 normalized_medias.append(normalized)
            
    #         return normalized_medias
    #     except Exception as e:
    #         self.logger.error(f"사용자 미디어 목록 가져오기 실패: {e}")
    #         return []
    
    def normalize_media_info(self, media_info: Dict) -> Dict:
        """인스타그램 미디어 정보를 표준화합니다.
        
        Args:
            media_info: 원본 미디어 정보
            
        Returns:
            표준화된 미디어 정보
        """
        media_types = {
            1: "image",
            2: "video",
            8: "album"
        }
        
        normalized = {
            'collection_id': media_info.get('saved_collections_id', ''),
            'feed_id': media_info.get('id', ''),
            # 'taken_at': '',
            'media_type': media_types[media_info.get("media_type", "")],
            'caption': (media_info.get("caption") or {}).get("text", ""),
            # 'like_count': media_info.get('like_count', 0),
            # 'comment_count': media_info.get('comment_count', 0),
            'media_url': '',
            'thumbnail_url': '',
            # 'username': '',
            # 'user_id': '',
            'url': f"https://www.instagram.com/p/{media_info.get('code', '')}/",
        }
        
        # # 작성 시간 변환
        # if 'taken_at' in media_info:
        #     taken_at = media_info['taken_at']
        #     if isinstance(taken_at, (int, float)):
        #         normalized['taken_at'] = datetime.datetime.fromtimestamp(taken_at).strftime('%Y-%m-%d %H:%M:%S')
        #     else:
        #         normalized['taken_at'] = str(taken_at)
        
        # 캡션 처리
        # if 'caption' in media_info and media_info['caption']:
        #     normalized['caption'] = media_info['caption'].get('text', '')
        
        # # 사용자 정보 처리
        # if 'user' in media_info:
        #     user = media_info['user']
        #     normalized['username'] = user.get('username', '')
        #     normalized['user_id'] = user.get('pk', '')
        #     normalized['full_name'] = user.get('full_name', '')
        
        # 미디어 URL 처리 (미디어 타입에 따라)
        if media_info.get('media_type') == 1:  # Image
            if 'image_versions2' in media_info and 'candidates' in media_info['image_versions2']:
                candidates = media_info['image_versions2']['candidates']
                if candidates:
                    normalized['media_url'] = candidates[0].get('url', '')
                    normalized['thumbnail_url'] = candidates[-1].get('url', '') if len(candidates) > 1 else candidates[0].get('url', '')
        
        elif media_info.get('media_type') == 2:  # Video
            if 'video_versions' in media_info:
                videos = media_info['video_versions']
                if videos:
                    normalized['media_url'] = videos[0].get('url', '')
            
            # 썸네일 URL
            if 'image_versions2' in media_info and 'candidates' in media_info['image_versions2']:
                candidates = media_info['image_versions2']['candidates']
                if candidates:
                    normalized['thumbnail_url'] = candidates[0].get('url', '')
        
        elif media_info.get('media_type') == 8:  # Album
            if 'carousel_media' in media_info:
                # 첫 번째 미디어 아이템으로 대표 URL 설정
                carousel = media_info['carousel_media']
                if carousel:
                    first_item = carousel[0]
                    if first_item.get('media_type') == 1:  # Photo
                        if 'image_versions2' in first_item and 'candidates' in first_item['image_versions2']:
                            candidates = first_item['image_versions2']['candidates']
                            if candidates:
                                normalized['media_url'] = candidates[0].get('url', '')
                                normalized['thumbnail_url'] = candidates[-1].get('url', '') if len(candidates) > 1 else candidates[0].get('url', '')
                    elif first_item.get('media_type') == 2:  # Video
                        if 'video_versions' in first_item:
                            videos = first_item['video_versions']
                            if videos:
                                normalized['media_url'] = videos[0].get('url', '')
                        
                        # 썸네일 URL
                        if 'image_versions2' in first_item and 'candidates' in first_item['image_versions2']:
                            candidates = first_item['image_versions2']['candidates']
                            if candidates:
                                normalized['thumbnail_url'] = candidates[0].get('url', '')
                
                # 캐러셀 아이템 목록 추가
                carousel_items = []
                for item in carousel:
                    item_info = {
                        'media_type': item.get('media_type', 1),
                        'media_type_name': media_types.get(item.get('media_type', 1), "image"),
                    }
                    
                    if item.get('media_type') == 1:  # Photo
                        if 'image_versions2' in item and 'candidates' in item['image_versions2']:
                            candidates = item['image_versions2']['candidates']
                            if candidates:
                                item_info['url'] = candidates[0].get('url', '')
                    elif item.get('media_type') == 2:  # Video
                        if 'video_versions' in item:
                            videos = item['video_versions']
                            if videos:
                                item_info['url'] = videos[0].get('url', '')
                    
                    carousel_items.append(item_info)
                
                normalized['carousel_media'] = carousel_items
        
        # # 위치 정보 처리
        # if 'location' in media_info and media_info['location']:
        #     location = media_info['location']
        #     normalized['location'] = {
        #         'name': location.get('name', ''),
        #         'address': location.get('address', ''),
        #         'city': location.get('city', ''),
        #         'lat': location.get('lat', 0.0),
        #         'lng': location.get('lng', 0.0),
        #         'pk': location.get('pk', 0)
        #     }
        
        # 해시태그 처리
        # if 'caption' in media_info and media_info['caption'] and media_info['caption'].get('text', ''):
        #     caption_text = media_info['caption']['text']
        hashtags = re.findall(r'#(\w+)', normalized['caption'])
        normalized['hashtags'] = hashtags
        
        return normalized

    def download_media(self, media_info: Dict, output_dir: str = './downloaded') -> str:
        """미디어를 다운로드합니다.
        
        Args:
            media_info: 정규화된 미디어 정보
            output_dir: 출력 디렉토리
            
        Returns:
            다운로드된 파일 경로 또는 오류 메시지
        """
        try:
            # 출력 디렉토리 생성
            os.makedirs(output_dir, exist_ok=True)
            
            media_type = media_info.get('media_type')
            code = media_info.get('code', '')
            
            # 캐러셀 미디어 처리
            if media_type == 8 and 'carousel_media' in media_info:
                downloaded_files = []
                for idx, item in enumerate(media_info['carousel_media']):
                    if 'url' in item:
                        item_type = item.get('media_type')
                        extension = 'mp4' if item_type == 2 else 'jpg'
                        filename = f"{code}_{idx+1}.{extension}"
                        filepath = os.path.join(output_dir, filename)
                        
                        # 파일 다운로드
                        self._download_file(item['url'], filepath)
                        downloaded_files.append(filepath)
                
                return f"다운로드 완료: {len(downloaded_files)}개 파일"
            
            # 단일 미디어 처리
            else:
                media_url = media_info.get('media_url', '')
                if not media_url:
                    return "다운로드할 URL이 없습니다"
                
                # 확장자 결정
                extension = 'mp4' if media_type == 2 else 'jpg'
                filename = f"{code}.{extension}"
                filepath = os.path.join(output_dir, filename)
                
                # 파일 다운로드
                self._download_file(media_url, filepath)
                return f"다운로드 완료: {filepath}"
        
        except Exception as e:
            self.logger.error(f"다운로드 실패: {e}")
            return f"다운로드 오류: {str(e)}"

    def _download_file(self, url: str, filepath: str) -> None:
        """지정된 URL에서 파일을 다운로드합니다.
        
        Args:
            url: 다운로드할 파일의 URL
            filepath: 저장할 파일 경로
        """
        try:
            response = requests.get(url, stream=True, timeout=10)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            self.logger.info(f"파일 다운로드 완료: {filepath}")
        except Exception as e:
            self.logger.error(f"파일 다운로드 실패: {url} -> {e}")
            raise

    def close(self):
        """클라이언트 연결을 종료합니다."""
        if self.client:
            self.logger.info("인스타그램 클라이언트 연결 종료")
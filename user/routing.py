from django.urls import re_path
from user import consumers

# WebSocket 경로 정의 (사용자 로그인/로그아웃 상태 변경)
websocket_urlpatterns = [
    re_path(r'ws/user/status/$', consumers.UserStatusConsumer.as_asgi()),  # 사용자 상태 관리 Consumer
]
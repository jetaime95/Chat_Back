import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from middlewares.jwt_middleware import JWTAuthMiddleware
from user import routing as user_routing  # user 앱의 routing.py 임포트

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chat_project.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),  # HTTP 요청 처리
    "websocket": JWTAuthMiddleware(
        URLRouter([
            # user 앱의 WebSocket 경로
            *user_routing.websocket_urlpatterns,
        ])
    ),
})

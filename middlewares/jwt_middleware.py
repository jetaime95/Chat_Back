from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth.models import AnonymousUser
from channels.db import database_sync_to_async
from urllib.parse import parse_qs
from django.utils.deprecation import MiddlewareMixin
from channels.middleware import BaseMiddleware

User = get_user_model()

class UniversalJWTAuthMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # HTTP 요청 처리 로직
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            try:
                validated_token = AccessToken(token)
                user_id = validated_token['user_id']
                user = User.objects.get(id=user_id)
                request.user = user
                print(f"JWT Middleware (HTTP): User authenticated - {user}")
            except Exception as e:
                print(f"JWT Authentication Error (HTTP): {e}")
                request.user = AnonymousUser()
        else:
            request.user = AnonymousUser()
        return None

class JWTWebSocketMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        # 토큰 추출
        headers = dict(scope.get('headers', []))
        auth_header = headers.get(b'authorization', b'').decode()
        
        query_string = scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)
        
        # 토큰 선택 (헤더 우선, 그 다음 쿼리 파라미터)
        token = None
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        elif 'token' in query_params:
            token_value = query_params['token'][0]
            # Bearer 접두사가 있으면 제거
            if token_value.startswith('Bearer '):
                token = token_value.split(' ')[1]
            else:
                token = token_value
        
        # 토큰 인증
        user = await self.authenticate_websocket(token)
        
        # 스코프에 사용자 설정
        scope['user'] = user
        
        return await super().__call__(scope, receive, send)

    @database_sync_to_async
    def authenticate_websocket(self, token):
        # WebSocket 인증 로직
        if not token:
            return AnonymousUser()
        
        try:
            validated_token = AccessToken(token)
            user_id = validated_token['user_id']
            user = User.objects.get(id=user_id)
            print(f"JWT Middleware (WebSocket): User authenticated - {user}")
            return user
        except Exception as e:
            print(f"JWT Authentication Error (WebSocket): {e}")
            return AnonymousUser()
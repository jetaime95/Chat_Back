from urllib.parse import parse_qs
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async

User = get_user_model()

class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        # URL에서 query_string을 받아옴
        query_string = scope.get("query_string", b"").decode("utf-8")
        query_params = parse_qs(query_string)
        
        # token 파라미터 추출
        token = query_params.get("token", [None])[0]

        # JWT Token이 Bearer 형식일 경우, 'Bearer ' 부분을 제거하고 실제 토큰만 사용
        if token and token.startswith("Bearer "):
            token = token[7:]

        print(f"JWT 미들웨어: 수신된 토큰 - {token}")

        if token:
            try:
                # AccessToken 검증
                validated_token = AccessToken(token)
                user_id = validated_token["user_id"]

                # 데이터베이스에서 사용자 조회 (비동기로 처리)
                user = await self.get_user(user_id)
                scope["user"] = user

                print(f"JWT 미들웨어: 사용자 설정 - {scope['user']}")
            except Exception as e:
                print(f"JWT 오류: {e}")
                scope["user"] = AnonymousUser()
        else:
            scope["user"] = AnonymousUser()

        # 다음 미들웨어 또는 라우터로 요청 전달
        return await super().__call__(scope, receive, send)
    
    @database_sync_to_async
    def get_user(self, user_id):
        return User.objects.get(id=user_id)

class JWTAuthMiddlewareStack:
    def __init__(self, inner):
        self.inner = inner

    def __call__(self, scope):
        return JWTAuthMiddleware(self.inner)
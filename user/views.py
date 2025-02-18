import logging
from asgiref.sync import async_to_sync
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django_redis import get_redis_connection
from django.contrib.auth.hashers import check_password
from django.core.exceptions import ValidationError
from rest_framework import status, permissions
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from channels.layers import get_channel_layer
from user.models import User, Friendship
from user.serializers import (UserSerializer, CustomObtainPairSerializer,  UserProfileSerializers, 
                              UserProfileUpdateSerializers, EmailVerificationSerializer, VerifyCodeSerializer,
                              UserSearchSerializer, FriendshipSerializer, FriendRequestActionSerializer, PasswordChangeSerializer)

logger = logging.getLogger(__name__)

#이메일 인증
class EmailVerificationView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        email_verification = User.objects.filter(email=request.data['email'])
        if email_verification:
            return Response({
                "message": "이미 가입된 이메일입니다."
            }, status=status.HTTP_400_BAD_REQUEST)
        else:
            serializer = EmailVerificationSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response({
                    "message": "인증번호가 발송되었습니다."
                }, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
#인증번호 확인
class VerifyCodeView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = VerifyCodeSerializer(data=request.data)
        if serializer.is_valid():
            return Response({
                "message": "이메일 인증이 완료되었습니다."
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#회원가입
class UserView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        if User.objects.filter(email = request.data["email"]):
            return Response({"message" : "이미 가입된 이메일 입니다.\n다시 시도해주세요."}, status=status.HTTP_400_BAD_REQUEST)
        
        elif User.objects.filter(username = request.data["username"]):
            return Response({"message" : "중복된 닉네임이 있습니다.\n다시 시도해주세요."}, status=status.HTTP_400_BAD_REQUEST)
        
        else:
            serializer = UserSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response({"message" : "회원가입을 축하합니다!"}, status=status.HTTP_201_CREATED)
            else:
                return Response({"message" : f"${serializer.errors}"}, status=status.HTTP_400_BAD_REQUEST)

# 로그인 
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomObtainPairSerializer

    def post(self, request, *args, **kwargs):
        try:
            response = super().post(request, *args, **kwargs)
            
            if response.status_code == 200:
                email = request.data.get('email')
                try:
                    user = User.objects.get(email=email)
                    
                    # 기존 토큰 정리 로직
                    outstanding_tokens = OutstandingToken.objects.filter(user_id=user.id)
                    BlacklistedToken.objects.filter(token__in=outstanding_tokens).delete()
                    outstanding_tokens.delete()
                    
                    # Redis 블랙리스트 토큰 삭제
                    try:
                        redis = get_redis_connection("default")
                        blacklist_key = f"blacklist_user_{user.id}_refresh_token"
                        if redis.exists(blacklist_key):
                            redis.delete(blacklist_key)
                    except Exception as e:
                        print(f"Redis 작업 중 에러: {str(e)}")

                    # 사용자 상태 변경
                    user.is_online = True
                    user.save()
                
                except User.DoesNotExist:
                    print(f"User not found: {email}")
                except Exception as e:
                    print(f"토큰 삭제 중 에러: {str(e)}")
            
            return response

        except Exception as e:
            print(f"로그인 처리 중 에러 발생: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return Response({"error": "Refresh token is required"}, status=400)

            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except Exception as e:
                logging.error(f"Token blacklist error: {str(e)}")
                return Response({"error": "Invalid token"}, status=400)

            user = request.user
            user.is_online = False
            user.save()

            try:
                group_name = f'user_{user.id}'
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    group_name,
                    {
                        'type': 'status_message',
                        'message': '로그아웃 되었습니다.',
                        'is_online': user.is_online,
                        'user_id': user.id,
                        'username': user.username,
                        'updated_at': user.updated_at.isoformat()
                    }
                )
                logger.info(f"Logout status message sent for user {user.id}")
            except Exception as e:
                logger.error(f"WebSocket message error in logout: {str(e)}")

            return Response({"message": "로그아웃 완료"}, status=200)

        except Exception as e:
            logging.error(f"Logout process error: {str(e)}")
            return Response({"error": str(e)}, status=400)

#프로필 페이지
class ProfileView(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request):
        user = User.objects.get(id=request.user.id)
        serializer_user = UserProfileSerializers(user)
        return Response(serializer_user.data, status=status.HTTP_200_OK)
    
#프로필 수정  
    def put(self, request, *args, **kwargs):
        user = get_object_or_404(User, id=request.user.id)
        serializer = UserProfileUpdateSerializers(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#회원탈퇴
    def post(self, request):
        user = get_object_or_404(User, id=request.user.id)
        input_password = request.data.get('password')
        
        # check_password 함수를 이용해 평문 비밀번호와 해시된 비밀번호 비교
        if check_password(input_password, user.password):
            user.delete()
            return Response({"message": "성공"}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "실패"}, status=status.HTTP_400_BAD_REQUEST)
        
#비밀번호 변경
class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data)
        
        if serializer.is_valid():
            user = request.user
            current_password = serializer.validated_data['current_password']
            new_password = serializer.validated_data['new_password']
            
            # 현재 비밀번호 확인
            if not user.check_password(current_password):
                return Response(
                    {"error": "현재 비밀번호가 일치하지 않습니다."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                # 새 비밀번호 설정
                user.set_password(new_password)
                user.save()
                
                return Response(
                    {"message": "비밀번호가 성공적으로 변경되었습니다."}, 
                    status=status.HTTP_200_OK
                )
            
            except ValidationError as e:
                return Response(
                    {"error": str(e)}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
        return Response(
            serializer.errors, 
            status=status.HTTP_400_BAD_REQUEST
        )
        
# 사용자 검색
class SearchUserView(APIView):
    permission_classes = [IsAuthenticated]  # 인증된 사용자만 접근 가능
    def get(self, request):
        username = request.query_params.get('username', None)  # 쿼리 파라미터에서 username을 가져옴
        if username:
            # username으로 사용자 검색 (대소문자 구분 없이)
            users = User.objects.filter(username__icontains=username).exclude(id=request.user.id)  # 나를 제외하고 user 필터링
            # 직렬화기를 사용하여 사용자 데이터 직렬화
            serializer = UserSearchSerializer(users, many=True)
            return Response({"users": serializer.data}, status=200)  # 사용자 목록 반환
        return Response({"error": "사용자가 존재하지 않습니다."}, status=400)  # username이 없을 경우 오류 메시지
        
# 친구 요청 보내기
class SendFriendRequestView(APIView):
    permission_classes = [IsAuthenticated]  # 인증된 사용자만 접근 가능
    def post(self, request):
        serializer = FriendRequestActionSerializer(data=request.data)  # 직렬화기 사용
        if serializer.is_valid():
            username = serializer.validated_data['username']  # 추가할 친구의 사용자 이름
            friend_user = get_object_or_404(User, username=username)  # 친구 사용자 조회
            
            # 이미 친구인지 확인
            existing_friendship = Friendship.objects.filter(
                (Q(from_user=request.user, to_user=friend_user) | Q(from_user=friend_user, to_user=request.user))
            ).first()  # 친구 관계가 존재하는지 확인
            
            if existing_friendship:
                return Response({"error": "이미 친구입니다."}, status=400)  # 이미 친구인 경우 오류 메시지
            # 친구 추가 요청 생성
            new_friendship = Friendship(from_user=request.user, to_user=friend_user)
            new_friendship.save()  # 친구 요청 저장
            
            return Response({"message": "친구 요청이 전송되었습니다."}, status=201)  # 성공 메시지
        return Response({"error": "유효하지 않은 요청입니다."}, status=400)  # 오류 메시지

# 친구 요청 보낸 목록 조회
class SentFriendRequestListView(APIView):
    permission_classes = [IsAuthenticated]  # 인증된 사용자만 접근 가능
    def get(self, request):
        # 현재 사용자가 보낸 친구 요청 목록을 조회하되, accepted가 False인 요청만 필터링
        sent_requests = Friendship.objects.filter(from_user=request.user, accepted=False)
        # 직렬화기를 사용하여 요청 데이터 직렬화
        serializer = FriendshipSerializer(sent_requests, many=True)
        return Response({"sent_requests": serializer.data}, status=200)  # 보낸 친구 요청 목록 반환

# 친구 요청 받은 목록 조회
class ReceivedFriendRequestListView(APIView):
    permission_classes = [IsAuthenticated]  # 인증된 사용자만 접근 가능
    def get(self, request):
        # 현재 사용자가 받은 친구 요청 목록을 조회
        received_requests = Friendship.objects.filter(to_user=request.user, accepted=False)
        # 직렬화기를 사용하여 요청 데이터 직렬화
        serializer = FriendshipSerializer(received_requests, many=True)
        return Response({"received_requests": serializer.data}, status=200)  # 받은 친구 요청 목록 반환

# 친구 요청 수락
class AcceptFriendRequestView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        serializer = FriendRequestActionSerializer(data=request.data)  # 직렬화기 사용
        if serializer.is_valid():
            from_user = get_object_or_404(User, username=serializer.validated_data['username'])  # 닉네임으로 사용자 조회
            # 친구 요청을 찾고 수락
            friendship = get_object_or_404(Friendship, from_user=from_user, to_user=request.user)
            friendship.accepted = True  # 친구 요청 수락
            friendship.save()  # 변경 사항 저장
            return Response({"message": "친구 요청이 수락되었습니다."}, status=200)  # 성공 메시지
        return Response({"error": "유효하지 않은 요청입니다."}, status=400)  # 오류 메시지

# 친구 요청 거절
class RejectFriendRequestView(APIView):
    permission_classes = [IsAuthenticated]
    def delete(self, request):
        serializer = FriendRequestActionSerializer(data=request.data)  # 직렬화기 사용
        if serializer.is_valid():
            from_user = get_object_or_404(User, username=serializer.validated_data['username'])  # 닉네임으로 사용자 조회
            # 친구 요청을 찾고 삭제
            friendship = get_object_or_404(Friendship, from_user=from_user, to_user=request.user)
            friendship.delete()  # 친구 요청 거절 (삭제)
            return Response({"message": "친구 요청이 거절되었습니다."}, status=200)  # 성공 메시지
        return Response({"error": "유효하지 않은 요청입니다."}, status=400)  # 오류 메시지

# 친구 목록
class FriendListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):      # 현재 사용자의 친구 목록을 조회
        friends = Friendship.objects.filter(
        Q(from_user=request.user, accepted=True) | Q(to_user=request.user, accepted=True)
        ).distinct()
        # 친구 목록에서 친구 사용자 정보를 직렬화
        friend_usernames = [friend.to_user if friend.from_user == request.user else friend.from_user for friend in friends]  # 친구 객체를 가져옴
        serializer = UserSearchSerializer(friend_usernames, many=True)
        return Response({"friends_requests": serializer.data}, status=200)  # 친구 목록을 JSON 형식으로 반환
    
# 친구 삭제
class DeleteFriendView(APIView):
    permission_classes = [IsAuthenticated]  # 인증된 사용자만 접근 가능

    def delete(self, request):
        serializer = FriendRequestActionSerializer(data=request.data)  # 직렬화기 사용
        if serializer.is_valid():
            username = serializer.validated_data['username']  # 삭제할 친구의 사용자 이름
            friend_user = get_object_or_404(User, username=username)  # 친구 사용자 조회
             # 친구 관계를 찾고 삭제 (from_user와 to_user 모두 확인)
            friendship = Friendship.objects.filter(
                (Q(from_user=request.user, to_user=friend_user) | Q(from_user=friend_user, to_user=request.user))
            ).first()  # 첫 번째 매칭되는 친구 관계를 찾음
            if friendship:
                friendship.delete()  # 친구 관계 삭제
                return Response({"message": "친구가 삭제되었습니다."}, status=200)  # 성공 메시지
            else:
                return Response({"error": "친구 관계가 존재하지 않습니다."}, status=404)  # 친구 관계가 없을 경우 오류 메시지
        return Response({"error": "유효하지 않은 요청입니다."}, status=400)  # 오류 메시지
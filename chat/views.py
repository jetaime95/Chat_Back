from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from asgiref.sync import async_to_sync
from user.models import User
from .models import ChatRoom
from .serializers import ChatRoomSerializer, ChatMessageSerializer
from chat.consumers import send_sidebar_update

class DirectChatRoomListView(APIView):
    """1대1 채팅방 목록을 조회하는 뷰"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # 사용자가 참여하고 있는 1대1 채팅방만 가져옴
        chat_rooms = ChatRoom.objects.filter(participants=request.user, room_type='direct').prefetch_related('participants')
        serializer = ChatRoomSerializer(chat_rooms, many=True, context={'request': request})
        return Response(serializer.data)

class CreateDirectChatRoomView(APIView):
    """1대1 채팅방을 생성하는 뷰"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        other_user_id = request.data.get('user_id')
        if not other_user_id:
            return Response({"error": "대화 상대가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)
        # 자기 자신과의 채팅방 생성 방지
        if int(other_user_id) == request.user.id:
            return Response({"error": "자기 자신과는 채팅할 수 없습니다."}, status=status.HTTP_400_BAD_REQUEST)
        other_user = get_object_or_404(User, id=other_user_id)
        # 이미 존재하는 1대1 채팅방인지 확인
        existing_room = ChatRoom.objects.filter(participants=request.user, room_type='direct').filter(participants=other_user).first()
        
        if existing_room:
            serializer = ChatRoomSerializer(existing_room, context={'request': request})
            return Response(serializer.data)

        try:
            # 새로운 채팅방 생성
            chat_room = ChatRoom.objects.create(room_type="direct")
            chat_room.participants.add(request.user, other_user)

            # WebSocket 사이드바 업데이트
            async_to_sync(send_sidebar_update)(request.user, other_user)

            serializer = ChatRoomSerializer(chat_room, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except:
            return Response({"error": "채팅방 생성 중 오류가 발생했습니다."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DirectChatMessageView(APIView):
    """1대1 채팅방의 메시지를 조회하고 전송하는 뷰"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, room_id):
        # 해당 채팅방이 1대1 채팅방이고 사용자가 참여자인지 확인
        chat_room = get_object_or_404(ChatRoom, id=room_id, room_type='direct', participants=request.user)
        
        # 상대방 정보 가져오기
        other_participant = chat_room.participants.exclude(id=request.user.id).first()
        if not other_participant:
            return Response({"error": "상대방 정보를 가져올 수 없습니다."}, status=400)
        
        # 메시지 읽음 처리
        unread_messages = chat_room.messages.filter(is_read=False).exclude(sender=request.user)
        unread_messages.update(is_read=True)
        
        # 최근 100개의 메시지만 조회
        messages = chat_room.messages.all()[:100]
        serializer = ChatMessageSerializer(messages, many=True)
        
        # 상대방 정보 추가
        response_data = {
            "messages": serializer.data,
            "other_participant": {
                "id": other_participant.id,
                "username": other_participant.username,
                "is_online": other_participant.is_online,
                "created_at": other_participant.created_at,
                "image": str(other_participant.image)
            }
        }
        
        return Response(response_data)
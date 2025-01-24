import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from django.core.exceptions import ValidationError
from django.utils.html import escape
from .models import ChatRoom, ChatMessage
from .serializers import ChatMessageSerializer, ChatRoomSerializer

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs'].get('room_id')
        
        if not self.room_id:
            await self.close()
            return
            
        # 사용자 인증 확인
        if not self.scope["user"].is_authenticated:
            await self.close()
            return
        
        try:
            # 채팅방 접근 권한 및 초기화
            room_access = await self.initialize_room()
            if not room_access:
                await self.close()
                return

            # 채팅방 그룹 이름 설정
            self.room_group_name = f"chat_room_{self.room_id}"
            
            # 채팅방 그룹에 참여
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )

            # 연결 수락
            await self.accept()
            
        except Exception as e:
            await self.close()
            return

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            # 채팅방 그룹에서 제거
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type', 'message')
            
            if message_type == 'message':
                await self.handle_chat_message(data)
                    
        except json.JSONDecodeError:
            await self.send_error("잘못된 메시지 형식입니다.")
        except Exception as e:
            await self.send_error(f"메시지 처리 중 오류가 발생했습니다: {str(e)}")

    async def handle_chat_message(self, data):
        message_content = data.get('message', '').strip()
        
        # 메시지 유효성 검사
        if not await self.validate_message(message_content):
            return

        try:
            # 메시지 저장
            message = await self.save_message(message_content)
            
            # 메시지 시리얼라이즈
            message_data = await self.serialize_message(message)
            
            # 그룹에 메시지 전송
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'message',
                    'message': message_data
                }
            )
            
            # 사이드바 업데이트
            other_participant = await self.get_other_participant(message.room, self.scope["user"].id)
            await send_sidebar_update(self.scope["user"], other_participant)
        except Exception as e:
            await self.send_error(f"메시지 저장 중 오류가 발생했습니다: {str(e)}")

    async def message(self, event):
        """채팅 메시지를 클라이언트에게 전송"""
        await self.send(text_data=json.dumps({
            "type": "message",  # message 타입으로 보내기
            "message": event['message']  # 메시지 내용
        }))

    async def send_error(self, message):
        """에러 메시지 전송"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message
        }))

    @database_sync_to_async
    def initialize_room(self):
        """채팅방 초기화 및 접근 권한 확인"""
        try:
            self.room = ChatRoom.objects.select_related().get(id=self.room_id)
            return self.room.participants.filter(id=self.scope["user"].id).exists()
        except ChatRoom.DoesNotExist:
            return False
        except Exception:
            return False

    @database_sync_to_async
    def validate_message(self, content):
        """메시지 유효성 검사"""
        if not content:
            self.send_error("메시지 내용이 비어있습니다.")
            return False
            
        if len(content) > 1000:  # 최대 길이 제한
            self.send_error("메시지가 너무 깁니다. (최대 1000자)")
            return False
            
        return True

    @database_sync_to_async
    def save_message(self, content):
        """메시지 저장"""
        try:
            sanitized_content = escape(content)  # XSS 방지
            return ChatMessage.objects.create(
                room=self.room,
                sender=self.scope["user"],
                content=sanitized_content
            )
        except Exception as e:
            raise ValidationError(f"메시지 저장 실패: {str(e)}")
    
    @database_sync_to_async
    def serialize_message(self, message):
        """메시지 시리얼라이즈"""
        return ChatMessageSerializer(message).data
    
    @database_sync_to_async
    def get_other_participant(self, room, user_id):
        return room.participants.exclude(id=user_id).first()
    
class SidebarChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # 사용자 인증 확인
        if not self.scope["user"].is_authenticated:
            await self.close()
            return
        
        self.user_channel_name = f"sidebar_chat_{self.scope['user'].id}"
        
        # 채널 레이어에 참여
        await self.channel_layer.group_add(
            self.user_channel_name,
            self.channel_name
        )
        
        await self.accept()
    
        # 초기 채팅방 목록 전송
        await self.send_chat_room_list()

    async def disconnect(self, close_code):
        # 채널 레이어에서 제거
        if hasattr(self, 'user_channel_name'):
            await self.channel_layer.group_discard(
                self.user_channel_name,
                self.channel_name
            )

    async def receive(self, text_data):
        # 클라이언트로부터 받은 메시지 처리 (필요한 경우)
        pass

    async def send_chat_room_list(self):
        """현재 사용자의 채팅방 목록 직렬화 및 전송"""
        chat_rooms = await self.get_chat_rooms()
        await self.send(text_data=json.dumps({
            'type': 'chat_room_list',
            'rooms': chat_rooms
        }))

    async def chat_message(self, event):
        """새 메시지 수신 시 사이드바 업데이트"""
        await self.send_chat_room_list()

    async def update_chat_rooms(self, event):
        """채팅방 업데이트 이벤트 처리"""
        await self.send_chat_room_list()

    @database_sync_to_async
    def get_chat_rooms(self):
        """사용자의 다이렉트 메시지 채팅방 목록 가져오기"""
        chat_rooms = ChatRoom.objects.filter(
            participants=self.scope["user"], 
            room_type='direct'
        ).prefetch_related('participants', 'messages')
        
        # 시리얼라이저 컨텍스트 생성 (request 대신 수동으로 user 전달)
        class MockRequest:
            def __init__(self, user):
                self.user = user
        
        mock_request = MockRequest(self.scope["user"])
        serializer = ChatRoomSerializer(
            chat_rooms, 
            many=True, 
            context={'request': mock_request}
        )
        
        return serializer.data

# 채팅 업데이트 헬퍼 함수 (전역 함수로 이동)
async def send_sidebar_update(sender, recipient):
    """
    메시지 전송 시 양쪽 사용자의 사이드바 업데이트
    """
    channel_layer = get_channel_layer()

    # 발신자 사이드바 업데이트
    await channel_layer.group_send(
        f"sidebar_chat_{sender.id}",
        {
            'type': 'chat_message'
        }
    )
    
    # 수신자 사이드바 업데이트
    await channel_layer.group_send(
        f"sidebar_chat_{recipient.id}",
        {
            'type': 'chat_message'
        }
    )
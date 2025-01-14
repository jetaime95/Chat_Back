from channels.generic.websocket import AsyncWebsocketConsumer
import json
import logging
from channels.db import database_sync_to_async
from django.db.models import Q
from user.models import Friendship, User

logger = logging.getLogger(__name__)

class UserStatusConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # 실제 User 객체를 가져옴
        self.user = await self.get_user()
        if not self.user:
            await self.close()
            return
            
        self.group_name = f'user_{self.user.id}'
        
        logger.info(f"WebSocket connecting for user {self.user.id} in group {self.group_name}")
        
        # 자신의 그룹에 연결
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        # 친구들의 그룹에도 연결
        friend_groups = await self.get_friend_groups()
        for friend_group in friend_groups:
            await self.channel_layer.group_add(
                friend_group,
                self.channel_name
            )

        await self.accept()
        logger.info(f"WebSocket connection accepted for user {self.user.id}")

    @database_sync_to_async
    def get_user(self):
        # scope에서 user를 가져와서 실제 User 객체로 변환
        if self.scope["user"] and self.scope["user"].is_authenticated:
            return User.objects.filter(id=self.scope["user"].id).first()
        return None

    @database_sync_to_async
    def get_friend_groups(self):
        # 수락된 친구 관계만 가져오기
        friendships = Friendship.objects.filter(
            (Q(from_user_id=self.user.id) | Q(to_user_id=self.user.id)),
            accepted=True
        ).select_related('from_user', 'to_user')
        
        friend_groups = []
        for friendship in friendships:
            friend = friendship.to_user if friendship.from_user_id == self.user.id else friendship.from_user
            friend_groups.append(f'user_{friend.id}')
        return friend_groups

    async def disconnect(self, close_code):
        if not hasattr(self, 'user') or not self.user:
            return
            
        logger.info(f"WebSocket disconnecting for user {self.user.id}")
        
        # 자신의 그룹에서 제거
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
        
        # 친구들의 그룹에서도 제거
        friend_groups = await self.get_friend_groups()
        for friend_group in friend_groups:
            await self.channel_layer.group_discard(
                friend_group,
                self.channel_name
            )

    async def receive(self, text_data):
        if not hasattr(self, 'user') or not self.user:
            return
            
        try:
            data = json.loads(text_data)
            message = data.get('message', '')
            status = data.get('status', '')
            
            logger.info(f"Received message for user {self.user.id}: {message}, status: {status}")

            # 자신과 친구들의 그룹에 상태 변경 메시지 전송
            friend_groups = await self.get_friend_groups()
            groups_to_notify = [self.group_name] + friend_groups
            
            for group in groups_to_notify:
                await self.channel_layer.group_send(
                    group,
                    {
                        'type': 'status_message',
                        'message': message,
                        'status': status,
                        'user_id': self.user.id,
                        'username': self.user.username
                    }
                )
        except Exception as e:
            logger.error(f"Error in receive: {str(e)}")
            await self.send(text_data=json.dumps({
                'error': str(e)
            }))

    async def status_message(self, event):
        try:
            logger.info(f"Sending status message: {event}")
            await self.send(text_data=json.dumps({
                'type': 'status_update',
                'message': event['message'],
                'status': event['status'],
                'user_id': event['user_id'],
                'username': event['username']
            }))
        except Exception as e:
            logger.error(f"Error in status_message: {str(e)}")
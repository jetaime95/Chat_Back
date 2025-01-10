from channels.generic.websocket import AsyncWebsocketConsumer
import json

class UserStatusConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        # 사용자별로 고유한 채널 그룹 설정 (예: 사용자 ID)
        self.group_name = f'user_{self.user.id}'

        # 그룹에 사용자 추가
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # 그룹에서 사용자 제거
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    # 실시간 알림 받기
    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data.get('message', '')

        # 실시간으로 메시지를 해당 그룹의 모든 사용자에게 전달
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'chat_message',  # 메시지 유형
                'message': message
            }
        )

    # 그룹에서 받은 메시지를 사용자에게 전달
    async def chat_message(self, event):
        message = event['message']
        await self.send(text_data=json.dumps({
            'message': message
        }))
from rest_framework import serializers
from .models import ChatMessage, ChatRoom

class ChatMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.username', read_only=True)
    sender_profile_image = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = ChatMessage
        fields = ['id', 'content', 'sender_name', 'sender_profile_image', 'created_at', 'is_read']
        read_only_fields = ['sender_name', 'sender_profile_image', 'created_at', 'is_read']
    
    def get_sender_profile_image(self, obj):
        """사용자 프로필 이미지 URL 반환"""
        if hasattr(obj.sender, 'image'):
            # User 모델에 직접 image 필드가 있는 경우
            return obj.sender.image.url if obj.sender.image else None
        elif hasattr(obj.sender, 'profile') and hasattr(obj.sender.profile, 'image'):
            # profile을 통해 image에 접근하는 경우
            return obj.sender.profile.image.url if obj.sender.profile.image else None
        return None

class ChatRoomSerializer(serializers.ModelSerializer):
    last_message = serializers.SerializerMethodField()
    other_participant = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatRoom
        fields = ['id', 'other_participant', 'last_message', 'unread_count', 'updated_at']
    
    def get_last_message(self, obj):
        last_message = obj.messages.last()
        if last_message:
            return ChatMessageSerializer(last_message).data
        return None
    
    def get_other_participant(self, obj):
        request = self.context.get('request')
        other_user = obj.participants.exclude(id=request.user.id).first()
        return {'id': other_user.id, 'username': other_user.username, 'is_online': other_user.is_online, 'image': str(other_user.image)} if other_user else None
    
    def get_unread_count(self, obj):
        request = self.context.get('request')
        return obj.messages.filter(is_read=False).exclude(sender=request.user).count()
from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('direct/rooms/', views.DirectChatRoomListView.as_view(), name='direct_room_list'),
    path('direct/rooms/create/', views.CreateDirectChatRoomView.as_view(), name='create_direct_room'),
    path('direct/rooms/<int:room_id>/messages/', views.DirectChatMessageView.as_view(), name='direct_room_messages'),
]
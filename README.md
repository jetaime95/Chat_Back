# Chat
WebSocket 기반 채팅 웹서비스

## 프로젝트 소개
실시간으로 메시지를 주고받을 수 있는 채팅 웹서비스입니다. WebSocket을 사용하여 클라이언트와 서버 간의 지속적인 연결을 유지하며, 실시간으로 채팅을 할 수 있습니다.

## 아키텍쳐
![image](https://github.com/user-attachments/assets/1c5c8974-de56-4dbf-8501-58981a3eaaa4)

## front-end github-address
[Chat_Frontend](https://github.com/jetaime95/Chat_Front)

## 주요 기능
- 실시간 메시지 전송
- 사용자 별 채팅방 생성
- 채팅 기록 저장 (데이터베이스 연동)
- 이메일을 통한 사용자 인증 (회원가입, 비밀번호 찾기)

## 주요 기능
1. 회원 가입 / 로그인
    - 이메일 인증을 통한 회원 가입
    - 이메일 인증을 통한 비밀번호 찾기
    - 로그인
2. 메인페이지
    - 사용자 친구 요청
    - 사용자 친구 수락 및 거절
    - 사용자 실시간 온/오프라인
3. 사이드바
    - 사용자 실시간 온/오프라인
    - 실시간 마지막 채팅 업데이트
    - 채팅 수신시 알림
4. 채팅 페이지
    - 실시간 1대1 채팅 서비스
4. 프로필
    - 프로필 수정
    - 비밀번호 변경
    - 회원탈퇴
    
## 사용 기술
- **Backend**: Django, Django Rest Framework
- **Frontend**: HTML, CSS, JavaScript
- **WebSocket**: Django Channels
- **Database**: SQLite (개발용), PostgreSQL (운영용)

## 웹페이지 주소
https://13.209.15.78

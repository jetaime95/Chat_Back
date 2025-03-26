# Python 이미지를 기반으로 사용
FROM python:3.12

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y wget

# dockerize 설치
RUN wget https://github.com/jwilder/dockerize/releases/download/v0.6.1/dockerize-linux-amd64-v0.6.1.tar.gz \
    && tar -xzvf dockerize-linux-amd64-v0.6.1.tar.gz \
    && mv dockerize /usr/local/bin/ \
    && rm dockerize-linux-amd64-v0.6.1.tar.gz

# 요구사항 파일 복사 및 설치
COPY ./Chat_Back/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 프로젝트 파일 복사
COPY ./Chat_Back /app

# PYTHONPATH 설정
ENV PYTHONPATH="/app:${PYTHONPATH}"

# Django 서버 포트 설정
EXPOSE 8000

# 실행 명령 수정
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "chat_project.asgi:application"]

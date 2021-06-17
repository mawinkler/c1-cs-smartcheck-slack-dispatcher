FROM python:3.9.5-alpine
# FROM docker:stable

# RUN apk add --no-cache python3 openssl-dev libffi-dev make build-base python3-dev py3-pip bash && \
#     apk del build-base python3-dev libffi-dev openssl-dev
RUN apk add --no-cache openssl-dev libffi-dev make build-base py3-pip bash && \
    apk del build-base libffi-dev openssl-dev

WORKDIR /app

# Install requirements
COPY requirements.txt ./requirements.txt
RUN pip3 install -r requirements.txt && \
    rm -f requirements.txt

# Copy in webhook listener script
COPY webhook_listener.py ./webhook_listener.py
CMD ["python3", "webhook_listener.py"]
EXPOSE 8000

#!/bin/bash

HUB_USERNAME=<YOUR DOCKER HUB USERNAME>
HUB_PASSWORD=<YOUR DOCKER HUB PASSWORD>

WEBHOOK_SECRET=trendmicro
SLACK_WEBHOOK_URL="https://hooks.slack.com/services/T025MGKP1NU/B0XXXXHF60G/Q2krrXXXXXXXXrXwFChDcG5B"
SLACK_CHANNEL="containersecurity"
DSSC_URL="192.168.1.121:8443"

echo ${HUB_PASSWORD} | docker login --username ${HUB_USERNAME} --password-stdin
docker build -t smartcheck-slack .
docker tag smartcheck-slack docker.io/${HUB_USERNAME}/smartcheck-slack:latest
docker push docker.io/${HUB_USERNAME}/smartcheck-slack:latest

cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  annotations:
    service.alpha.kubernetes.io/tolerate-unready-endpoints: "true"
  name: smartcheck-slack
  labels:
    app: smartcheck-slack
spec:
  type: ClusterIP
  ports:
  - port: 8000
    name: smartcheck-slack
    targetPort: 8000
  selector:
    app: smartcheck-slack
---
apiVersion: apps/v1
kind: Deployment
metadata:
  labels:
    app: smartcheck-slack
  name: smartcheck-slack
spec:
  replicas: 1
  selector:
    matchLabels:
      app: smartcheck-slack
  strategy: {}
  template:
    metadata:
      labels:
        app: smartcheck-slack
    spec:
      containers:
      - image: ${HUB_USERNAME}/smartcheck-slack:latest
        name: smartcheck-slack
        env:
        - name: WEBHOOK_SECRET
          value: ${WEBHOOK_SECRET}
        - name: SLACK_WEBHOOK_URL
          value: ${SLACK_WEBHOOK_URL}
        - name: SLACK_CHANNEL
          value: ${SLACK_CHANNEL}
        - name: DSSC_URL
          value: ${DSSC_URL}
status: {}
EOF

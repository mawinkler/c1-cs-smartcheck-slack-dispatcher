#!/bin/bash

REGISTRY_IP=<REGISTRY HOST>
REGISTRY_USERNAME=<REGISTRY USERNAME>
REGISTRY_PASSWORD=<REGISTRY PASSWORD>
REGISTRY_PORT=<REGISTRY PORT>
REGISTRY_EMAIL=<REGISTRY EMAIL>

WEBHOOK_SECRET=trendmicro
SLACK_WEBHOOK_URL="https://hooks.slack.com/services/T025MGKP1NU/B0XXXXHF60G/Q2krrXXXXXXXXrXwFChDcG5B"
SLACK_CHANNEL="containersecurity"
DSSC_URL="192.168.1.121:8443"

echo ${REGISTRY_PASSWORD} | docker login https://${REGISTRY_IP}:${REGISTRY_PORT} --username ${REGISTRY_USERNAME} --password-stdin
docker build -t smartcheck-slack .
docker tag smartcheck-slack ${REGISTRY_IP}:${REGISTRY_PORT}/smartcheck-slack:latest
docker push ${REGISTRY_IP}:${REGISTRY_PORT}/smartcheck-slack:latest

kubectl create secret docker-registry regcred --docker-server=${REGISTRY_IP}:${REGISTRY_PORT} --docker-username=${REGISTRY_USERNAME} --docker-password=${REGISTRY_PASSWORD} --docker-email=${REGISTRY_EMAIL}

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
      - image: ${REGISTRY_IP}:${REGISTRY_PORT}/smartcheck-slack:latest
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
      imagePullSecrets:
      - name: regcred
status: {}
EOF

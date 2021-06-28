# Smart Check Slack Dispatcher

- [Smart Check Slack Dispatcher](#smart-check-slack-dispatcher)
  - [Run Environment: Docker](#run-environment-docker)
    - [Build](#build)
    - [Run](#run)
    - [Smart Check](#smart-check)
  - [Run Environment: Kubernetes](#run-environment-kubernetes)
  - [Support](#support)
  - [Contribute](#contribute)

Receives Smart Check webhooks and sends `completed-with-findings` scan results to a given Slack channel.

Code borrows the logic to compose the Slack message from <https://github.com/tsheth/DSSC-Slack-SAM-notifier> by @tsheth.

## Run Environment: Docker

### Build

```sh
docker build -t smartcheck-slack .
```

### Run

```sh
docker run --rm \
  -e WEBHOOK_SECRET="trendmicro" \
  -e SLACK_WEBHOOK_URL="https://hooks.slack.com/services/T025XXXXXNU/B026XXXXX0G/Q2krr9FJtBXXXXXXXhDcG5B" \
  -e SLACK_CHANNEL="containersecurity" \
  -e DSSC_URL="192.168.1.121:8443" \
  -p 8888:8000 \
  smartcheck-slack
```

### Smart Check

Create a webhook pointing to the container. e.g. <http://192.168.1.121:8888>.

Don't forget to define the webhook secret you specified in docker run.

## Run Environment: Kubernetes

There are two scripts within this repo:

`deploy-hub.sh`

and

`deploy-local.sh`

The `-hub` script builds the container image, pushes it to Docker Hub and creates the deployment. I do recommend to deploy it to the same namespace in which Smart Check is running as well. Finally, point the Web Hook within Smart Check to <http://smartcheck-slack:8000>. Done.

The `-local` effectively does the same but uses a private registry, so regcreds are created as well and kubernetes pulls the image from the private registry.

For both scripts, please adapt the variables to your needs.

For the impatient ones amongst us, you can run the following commands as well, your cluster will then pull the image from my Docher Hub account. Please set the variables according to your needs.

```sh
WEBHOOK_SECRET=trendmicro
SLACK_WEBHOOK_URL="https://hooks.slack.com/services/T025MGKP1NU/B0XXXXHF60G/Q2krrXXXXXXXXrXwFChDcG5B"
SLACK_CHANNEL="containersecurity"
DSSC_URL="192.168.1.121:8443"

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
      - image: mawinkler/smartcheck-slack:latest
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
```

## Support

This is an Open Source community project. Project contributors may be able to help, depending on their time and availability. Please be specific about what you're trying to do, your system, and steps to reproduce the problem.

For bug reports or feature requests, please [open an issue](../../issues). You are welcome to [contribute](#contribute).

Official support from Trend Micro is not available. Individual contributors may be Trend Micro employees, but are not official support.

## Contribute

I do accept contributions from the community. To submit changes:

1. Fork this repository.
1. Create a new feature branch.
1. Make your changes.
1. Submit a pull request with an explanation of your changes or additions.

I will review and work with you to release the code.

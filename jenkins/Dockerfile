FROM jenkins/jenkins:lts-jdk17
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-venv python3-pip curl git \
    && rm -rf /var/lib/apt/lists/*
RUN curl -fsSL https://download.docker.com/linux/static/stable/x86_64/docker-27.3.1.tgz \
    | tar xz --strip-components=1 -C /usr/local/bin docker/docker
RUN jenkins-plugin-cli --plugins workflow-aggregator git junit timestamper pipeline-stage-view
ENV JAVA_OPTS="-Djenkins.install.runSetupWizard=false"

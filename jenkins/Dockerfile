FROM jenkins/jenkins:lts-jdk17
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-venv python3-pip curl git docker.io \
    && rm -rf /var/lib/apt/lists/*
RUN jenkins-plugin-cli --plugins workflow-aggregator git junit timestamper pipeline-stage-view
ENV JAVA_OPTS="-Djenkins.install.runSetupWizard=false"

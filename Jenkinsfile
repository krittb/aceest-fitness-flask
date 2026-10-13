// Jenkins BUILD & quality gate for ACEest Fitness & Gym.
// Pulls the latest code from GitHub, performs a CLEAN build, lints,
// builds the Docker image and runs the Pytest suite inside the container.
pipeline {
    agent any

    options {
        timestamps()
        buildDiscarder(logRotator(numToKeepStr: '15'))
        disableConcurrentBuilds()
    }

    triggers {
        // Fallback if the GitHub webhook is unreachable: poll SCM every 5 min
        pollSCM('H/5 * * * *')
    }

    environment {
        IMAGE_NAME = 'aceest-fitness'
        IMAGE_TAG  = "${env.BUILD_NUMBER}"
    }

    stages {
        stage('Clean Workspace & Checkout') {
            steps {
                deleteDir()          // guarantees a clean build
                checkout scm         // latest code from GitHub
            }
        }

        stage('Build & Lint') {
            steps {
                sh '''
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements-dev.txt
                    python -m compileall -q app.py test_app.py
                    flake8 .
                '''
            }
        }

        stage('Docker Image Assembly') {
            steps {
                sh '''
                    docker build --target runtime -t ${IMAGE_NAME}:${IMAGE_TAG} -t ${IMAGE_NAME}:latest .
                    docker build --target test -t ${IMAGE_NAME}:test .
                '''
            }
        }

        stage('Automated Testing (in Docker)') {
            steps {
                sh 'docker run --rm -v "$PWD:/out" ${IMAGE_NAME}:test pytest -v --junitxml=/out/test-results.xml'
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'test-results.xml'
                }
            }
        }

        stage('Smoke Test') {
            steps {
                sh '''
                    docker run -d --rm --name aceest_smoke_${BUILD_NUMBER} -p 5050:5000 ${IMAGE_NAME}:latest
                    sleep 5
                    curl --fail http://localhost:5050/health
                '''
            }
            post {
                always {
                    sh 'docker stop aceest_smoke_${BUILD_NUMBER} || true'
                }
            }
        }
    }

    post {
        success { echo "Build #${env.BUILD_NUMBER} succeeded." }
        failure { echo "Build #${env.BUILD_NUMBER} failed - see console output." }
    }
}

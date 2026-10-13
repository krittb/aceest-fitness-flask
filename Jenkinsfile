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
        pollSCM('H/5 * * * *')
    }

    environment {
        IMAGE_NAME = 'aceest-fitness'
        IMAGE_TAG  = "${env.BUILD_NUMBER}"
    }

    stages {
        stage('Clean Workspace & Checkout') {
            steps {
                deleteDir()
                checkout scm
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
                sh '''
                    docker rm -f aceest_test || true
                    set +e
                    docker run --name aceest_test ${IMAGE_NAME}:test pytest -v --junitxml=/tmp/test-results.xml
                    rc=$?
                    docker cp aceest_test:/tmp/test-results.xml test-results.xml || true
                    docker rm -f aceest_test
                    exit $rc
                '''
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
                    docker rm -f aceest_smoke || true
                    docker run -d --name aceest_smoke ${IMAGE_NAME}:latest
                    for i in $(seq 1 15); do
                        if docker exec aceest_smoke python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')"; then
                            exit 0
                        fi
                        sleep 2
                    done
                    docker logs aceest_smoke
                    exit 1
                '''
            }
            post {
                always {
                    sh 'docker rm -f aceest_smoke || true'
                }
            }
        }
    }

    post {
        success { echo "Build #${env.BUILD_NUMBER} succeeded." }
        failure { echo "Build #${env.BUILD_NUMBER} failed - see console output." }
    }
}

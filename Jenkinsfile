pipeline {
    agent any

    options {
        timestamps()
    }

    environment {
        IMAGE_NAME = 'codejudge-app'
        APP_CONTAINER_NAME = 'codejudge-app'
        APP_HOST_PORT = '5001'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Install Dependencies') {
            steps {
                sh 'python3 -m venv .venv'
                sh '.venv/bin/python -m pip install --upgrade pip'
                sh '.venv/bin/python -m pip install -r requirements.txt'
            }
        }

        stage('Run Tests') {
            steps {
                sh '.venv/bin/python -m pytest -q'
            }
        }

        stage('Build Docker Image') {
            steps {
                sh 'docker build -t ${IMAGE_NAME}:${BUILD_NUMBER} .'
                sh 'docker tag ${IMAGE_NAME}:${BUILD_NUMBER} ${IMAGE_NAME}:latest'
            }
        }

        stage('Deploy') {
            steps {
                sh '''
                    set -eu
                    : "${DB_HOST:?Set DB_HOST in Jenkins environment or credentials}"
                    : "${DB_USER:?Set DB_USER in Jenkins environment or credentials}"
                    : "${DB_PASSWORD:?Set DB_PASSWORD in Jenkins credentials}"
                    : "${DB_NAME:?Set DB_NAME in Jenkins environment}"
                    : "${FLASK_SECRET_KEY:?Set FLASK_SECRET_KEY in Jenkins credentials}"

                    if docker container inspect "$APP_CONTAINER_NAME" >/dev/null 2>&1; then
                        docker rm --force "$APP_CONTAINER_NAME"
                    fi

                    docker run --detach \
                        --name "$APP_CONTAINER_NAME" \
                        --restart unless-stopped \
                        --publish "$APP_HOST_PORT:5000" \
                        --env DB_HOST \
                        --env DB_USER \
                        --env DB_PASSWORD \
                        --env DB_NAME \
                        --env DB_PORT \
                        --env FLASK_SECRET_KEY \
                        --env SESSION_COOKIE_SECURE \
                        "$IMAGE_NAME:$BUILD_NUMBER"
                '''
            }
        }

        stage('Health Check') {
            steps {
                sh '''
                    set -eu
                    for attempt in $(seq 1 12); do
                        status=$(docker inspect --format='{{.State.Health.Status}}' "$APP_CONTAINER_NAME")
                        if [ "$status" = "healthy" ]; then
                            echo "Deployment is healthy on port $APP_HOST_PORT."
                            exit 0
                        fi
                        sleep 5
                    done

                    docker logs "$APP_CONTAINER_NAME"
                    echo "Deployment did not become healthy within 60 seconds." >&2
                    exit 1
                '''
            }
        }
    }

    post {
        success {
            echo 'CodeJudge tests, image build, deployment, and health check succeeded.'
        }
        failure {
            echo 'CodeJudge pipeline failed. Review the failed stage output above.'
        }
    }
}
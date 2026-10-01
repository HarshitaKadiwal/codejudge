pipeline {
    agent any

    environment {
        IMAGE_NAME = 'codejudge-app'
        BUILD_TAG = "${env.BUILD_NUMBER ?: 'local'}"
        FULL_TAG = "${IMAGE_NAME}:${BUILD_TAG}"
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Install Dependencies') {
            steps {
                sh 'python3 -m venv venv'
                sh 'venv/bin/pip install --upgrade pip'
                sh 'venv/bin/pip install -r requirements.txt'
            }
        }

        stage('Run Tests') {
            steps {
                sh 'venv/bin/pytest -q'
            }
        }

        stage('Build Docker Image') {
            steps {
                sh "docker build -t ${FULL_TAG} ."
                sh "docker tag ${FULL_TAG} ${IMAGE_NAME}:latest || true"
            }
        }

        stage('Run Container & Health Check') {
    steps {
        sh 'docker rm -f codejudge_temp || true'
        sh "docker run -d --name codejudge_temp -p 5001:5000 ${FULL_TAG}"
        sh 'sleep 3'
        sh "docker exec codejudge_temp python -c \"import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:5000/health').read().decode())\""
        sh 'docker rm -f codejudge_temp'
    }
}
    }

    post {
        always {
            sh 'docker images | head -n 20'
        }
    }
}
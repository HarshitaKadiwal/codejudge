pipeline {
    agent any

    options {
        timestamps()
    }

    environment {
        APP_PORT = '5001'

        MYSQL_ROOT_PASSWORD = credentials('codejudge-mysql-root-password')
        DB_USER = credentials('codejudge-db-user')
        DB_PASSWORD = credentials('codejudge-db-password')
        DB_NAME = 'codejudge'
        DB_PORT = '3306'
        FLASK_SECRET_KEY = credentials('codejudge-flask-secret')

        // Keep Jenkins deployment separate from your local Compose project
        COMPOSE_PROJECT_NAME = 'codejudge-jenkins'
        DB_VOLUME_NAME = 'codejudge-jenkins-db'
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Run Tests') {
            steps {
                bat '''
                    docker run --rm -v "%CD%:/app" -w /app python:3.11-slim sh -c "pip install -r requirements.txt && pytest -q -p no:cacheprovider"
                '''
            }
        }

        stage('Build Docker Image') {
            steps {
                bat 'docker compose build'
            }
        }

        stage('Deploy') {
            steps {
                bat '''
                    docker rm --force codejudge-app 2>NUL
                    docker compose down --remove-orphans
                    docker compose up -d
                '''
            }
        }

        stage('Health Check') {
            steps {
                bat '''
                    echo Waiting for CodeJudge to become healthy...

                    for /L %%A in (1,1,12) do (
                        docker compose exec -T web python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health')" >NUL 2>&1

                        if not errorlevel 1 (
                            echo CodeJudge is healthy on port %APP_PORT%.
                            exit /B 0
                        )

                        timeout /T 5 /NOBREAK >NUL
                    )

                    echo CodeJudge health check failed.
                    docker compose ps
                    docker compose logs --no-color web
                    exit /B 1
                '''
            }
        }
    }

    post {
        success {
            echo 'CodeJudge pipeline completed successfully.'
        }

        failure {
            echo 'CodeJudge pipeline failed. Check the failed stage above.'
        }
    }
}
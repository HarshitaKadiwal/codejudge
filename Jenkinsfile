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

       stage('Run Tests') {
    steps {
        bat 'docker run --rm -v "%CD%:/app" -w /app python:3.11-slim sh -c "pip install -r requirements.txt && pytest -q -p no:cacheprovider"'
    }
}

        stage('Build Docker Image') {
            steps {
                bat 'docker build -t %IMAGE_NAME%:%BUILD_NUMBER% .'
                bat 'docker tag %IMAGE_NAME%:%BUILD_NUMBER% %IMAGE_NAME%:latest'
            }
        }

        stage('Deploy') {
            steps {
                bat '''
                    docker rm --force %APP_CONTAINER_NAME% 2>NUL || exit /B 0

                    docker run --detach ^
                        --name %APP_CONTAINER_NAME% ^
                        --restart unless-stopped ^
                        --publish %APP_HOST_PORT%:5000 ^
                        --env DB_HOST ^
                        --env DB_USER ^
                        --env DB_PASSWORD ^
                        --env DB_NAME ^
                        --env DB_PORT ^
                        --env FLASK_SECRET_KEY ^
                        --env SESSION_COOKIE_SECURE ^
                        %IMAGE_NAME%:%BUILD_NUMBER%
                '''
            }
        }

        stage('Health Check') {
            steps {
                bat '''
                    for /L %%A in (1,1,12) do (
                        for /F "delims=" %%H in ('docker inspect --format="{{.State.Health.Status}}" %APP_CONTAINER_NAME% 2^>NUL') do (
                            if "%%H"=="healthy" (
                                echo Deployment is healthy on port %APP_HOST_PORT%.
                                exit /B 0
                            )
                        )
                        timeout /T 5 /NOBREAK >NUL
                    )

                    docker logs %APP_CONTAINER_NAME%
                    echo Deployment did not become healthy within 60 seconds.
                    exit /B 1
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
pipeline {
    agent any

    environment {
        DOCKER_IMAGE = 'vmpranavan/aceest-fitness'
        K8S_NAMESPACE = 'aceest-fitness'
        // These credentials should be set in Jenkins:
        // DOCKER_CREDENTIALS_ID
        // KUBECONFIG_CREDENTIALS_ID
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Install Dependencies') {
            agent {
                docker { image 'python:3.11-slim' }
            }
            steps {
                sh 'pip install -r requirements.txt'
            }
        }

        stage('Lint') {
            agent {
                docker { image 'python:3.11-slim' }
            }
            steps {
                sh 'pip install flake8'
                sh 'flake8 app.py tests/ --count --select=E9,F63,F7,F82 --show-source --statistics'
            }
        }

        stage('Unit Tests') {
            agent {
                docker { image 'python:3.11-slim' }
            }
            steps {
                sh 'pip install -r requirements.txt'
                sh 'pytest tests/ -v --cov=app --cov-report=xml --cov-report=html --junitxml=test-results/results.xml'
            }
            post {
                always {
                    junit 'test-results/*.xml'
                    archiveArtifacts artifacts: 'htmlcov/**/*', allowEmptyArchive: true
                }
            }
        }

        stage('SonarQube Analysis') {
            environment {
                SCANNER_HOME = tool 'SonarQubeScanner'
            }
            steps {
                withSonarQubeEnv('SonarQubeServer') {
                    sh "${SCANNER_HOME}/bin/sonar-scanner"
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                script {
                    docker.build("${DOCKER_IMAGE}:${env.BUILD_NUMBER}")
                    docker.build("${DOCKER_IMAGE}:latest")
                }
            }
        }

        stage('Push Docker Image') {
            steps {
                script {
                    docker.withRegistry('https://index.docker.io/v1/', 'dockerhub-credentials') {
                        docker.image("${DOCKER_IMAGE}:${env.BUILD_NUMBER}").push()
                        docker.image("${DOCKER_IMAGE}:latest").push()
                    }
                }
            }
        }

        stage('Deploy to Kubernetes') {
            environment {
                KUBECONFIG = credentials('kubeconfig')
            }
            steps {
                sh '/usr/local/bin/kubectl apply -f k8s/namespace.yaml'
                
                // Deploying rolling update as default
                sh "sed -i 's|vmpranavan/aceest-fitness:latest|${DOCKER_IMAGE}:${env.BUILD_NUMBER}|g' k8s/rolling-update.yaml"
                sh '/usr/local/bin/kubectl apply -f k8s/rolling-update.yaml'
            }
        }
    }

    post {
        success {
            echo "Pipeline completed successfully."
        }
        failure {
            echo "Pipeline failed."
        }
    }
}

pipeline {
    agent {
        docker {
            image 'python:3.11-slim'
            args '-u root'
            reuseNode true
        }
    }
    environment {
        PIP_CACHE_DIR = "${WORKSPACE}/.cache/pip"
    }
    stages {
        stage('Install') {
            steps { sh 'python -m pip install -e ".[dev]"' }
        }
        stage('Check and demonstrate') {
            steps { sh 'python scripts/check.py' }
        }
    }
    post {
        always {
            junit allowEmptyResults: true, testResults: 'reports/unit-tests.xml,reports/*/junit.xml'
            archiveArtifacts allowEmptyArchive: true, artifacts: 'reports/**'
        }
    }
}

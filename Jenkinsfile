pipeline {
    agent { dockerfile true }
    stages {
        stage('Test') {
            steps {
                sh 'python ImageClean.py staging'
		sh 'sleep 30'
		sh 'python ImageClean.py staging delete'
            }
        }
    }
}

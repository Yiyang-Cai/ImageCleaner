pipeline {
    agent { dockerfile true }
    stages {
        stage('Test') {
            steps {
                sh 'python ImageCleaner.py staging'
		sh 'sleep 30'
		sh 'python ImageCleaner.py staging delete'
            }
        }
    }
}

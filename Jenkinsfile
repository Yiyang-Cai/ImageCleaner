pipeline {
    agent { dockerfile true }
    stages {
        stage('Cleaning') {
            steps {
                sh 'python ImageCleaner.py staging'
		sh 'python ImageCleaner.py staging delete'
		sh 'sleep 15'
		sh 'rm -f ImagesClean.csv'
		sh 'python ImageCleaner.py production'
		sh 'python ImageCleaner.py production delete'
            }
        }
    }
}

pipeline {
    agent { dockerfile true }
    stages {
        stage('STG') {
            steps {
                sh 'python ImageCleaner.py staging'
		sh 'python ImageCleaner.py staging delete'
	    }
	}
	stage('PRD') {
	    steps {
		sh 'rm -f ImagesClean.csv'
		sh 'python ImageCleaner.py production'
		sh 'python ImageCleaner.py production delete'
            }
        }
    }
}

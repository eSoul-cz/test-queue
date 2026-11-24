pipeline {
	agent { label 'quick || general' }

	options {
		disableConcurrentBuilds()
		skipDefaultCheckout(true)
		timestamps()
		timeout(time: 15, unit: 'MINUTES')
	}

	stages {
		stage('Checkout') {
			steps {
				deleteDir()
				checkout scm
			}
		}

		stage('Test') {
			steps {
				sh 'scripts/test'
			}
		}
	}
}

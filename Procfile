web: newrelic-admin run-program gunicorn totalimpactwebapp:app -b 0.0.0.0:$PORT -w 3
celery: celery -A tasks worker --loglevel=info
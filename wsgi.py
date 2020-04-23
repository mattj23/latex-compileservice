from latex import create_app, celery

app = create_app()

if __name__ == '__main__':
    app.run(host="0.0.0.0")


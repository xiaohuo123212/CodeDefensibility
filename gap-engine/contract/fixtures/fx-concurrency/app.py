from flask import Flask

app = Flask(__name__)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(threaded=True)
from flask import Flask
from openpyxl import Workbook

app = Flask(__name__)


@app.route("/export")
def export_excel():
    raise NotImplementedError("导出功能暂未实现")


@app.route("/login")
def login():
    return "ok"


if __name__ == "__main__":
    app.run()
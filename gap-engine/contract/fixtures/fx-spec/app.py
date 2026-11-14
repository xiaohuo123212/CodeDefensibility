from flask import Flask

app = Flask(__name__)


@app.route("/export")
def export():
    import openpyxl

    workbook = openpyxl.Workbook()
    workbook.active.append(["id", "name"])
    return {"rows": workbook.active.max_row - 1}


@app.route("/login")
def login():
    return {"ok": True}


if __name__ == "__main__":
    app.run()
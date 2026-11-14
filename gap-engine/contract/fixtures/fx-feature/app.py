from flask import Flask
from openpyxl import Workbook

app = Flask(__name__)


@app.get("/export")
def export_rows():
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["id", "name"])
    sheet.append([1, "demo"])
    return {"rows": sheet.max_row - 1}


if __name__ == "__main__":
    app.run()
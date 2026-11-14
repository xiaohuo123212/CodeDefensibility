# fx-feature

支持 Excel 导出。

## 内容

| 文件 | 说明 |
| --- | --- |
| `app.py` | Flask 应用入口，含 `/export` 路由 |
| `requirements.txt` | 运行依赖 |

## 本地运行

```bash
pip install -r requirements.txt
python app.py
curl http://127.0.0.1:5000/export
```
# fx-concurrency

支持 500 并发用户。

## 内容

| 文件 | 说明 |
| --- | --- |
| `app.py` | Flask 应用入口 |
| `gunicorn.conf.py` | gunicorn 进程配置：`workers = 4` |
| `requirements.txt` | 运行依赖 |

## 本地运行

```bash
pip install -r requirements.txt
python app.py
gunicorn -c gunicorn.conf.py app:app
```
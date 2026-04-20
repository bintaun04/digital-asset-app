# be/run.py
import uvicorn
import os
from pathlib import Path

# Đảm bảo chạy từ thư mục be/
os.chdir(Path(__file__).parent)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",           # "main:app" vì main.py nằm cùng thư mục với run.py
        host="0.0.0.0",
        port=8000,
        reload=True,          # Tự động reload khi code thay đổi (rất tiện khi dev)
        log_level="info"
    )
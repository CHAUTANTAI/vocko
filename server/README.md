# VocKO FastAPI Backend

## Structure
- `src/main.py` — API entrypoint
- `src/models.py` — Pydantic models
- `src/db.py` — MongoDB connection
- `src/api_auth.py` — Auth endpoints
- `src/api_decks.py` — Deck/flashcard endpoints
- `src/api_learning.py` — Learning session endpoints
- `src/services.py` — SRS queue + `user_progress` updates
- `src/init_indexes.py` — MongoDB index creation script

## Quickstart

```powershell
cd server
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
# copy .env.example to .env if you use it
python src/init_indexes.py
python -m uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

Sau khi bật venv, luôn có thể dùng `python -m pip` thay cho `pip` nếu lệnh `pip` không có trong PATH.

## Sử dụng MongoDB Atlas
- Tạo cluster trên https://cloud.mongodb.com/
- Lấy URI kết nối dạng:
  mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?appName=<appName>
- Thêm vào file .env:
  MONGO_URI=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?appName=<appName>
  MONGO_DB=vocko

## Kiểm tra kết nối

```bash
python src/init_indexes.py
```

Nếu thấy "Pinged your deployment. You successfully connected to MongoDB!" là OK.

## Next Steps
- Bổ sung test tích hợp API, refresh token rotation, CORS chặt cho production

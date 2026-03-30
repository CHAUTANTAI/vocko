# VocKO FastAPI Backend

## Structure
- `src/main.py` — API entrypoint
- `src/models.py` — Pydantic models
- `src/db.py` — MongoDB connection
- `src/api_auth.py` — Auth endpoints
- `src/api_decks.py` — Deck/flashcard endpoints
- `src/api_learning.py` — Learning session endpoints
- `src/services.py` — SRS/session/progress logic (to be implemented)
- `src/init_indexes.py` — MongoDB index creation script

## Quickstart

```bash
cd server
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python src/init_indexes.py
uvicorn src.main:app --reload
```

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
- Implement API logic and authentication
- Add SRS and session management logic
- Integrate with frontend

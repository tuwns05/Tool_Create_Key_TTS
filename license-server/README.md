# TTS License Server

FastAPI server chạy cục bộ để tạo payload license, tính thời hạn theo lịch và ký
bằng Ed25519. Payload được trả trong response chỉ nhằm hỗ trợ debug trên localhost.

## Chạy trên Windows PowerShell

```powershell
cd license-server
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Mở `.env` và thay placeholder bằng private key. Với cặp key **chỉ dùng để test**:

```dotenv
LICENSE_PRIVATE_KEY=4BI0ollUUzAioL_OdBEiq6at8zDb58ZbEhD4UtkgMgk
```

Không dùng test key trong production và không commit `.env`.

Khởi chạy server:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Mở Swagger tại <http://127.0.0.1:8000/docs>. Health check ở
<http://127.0.0.1:8000/health>.

Payload thử cho `POST /license/generate`:

```json
{
  "customer_name": "Test Customer",
  "email": "test@example.com",
  "mac": "F0:68:E3:C4:D1:A1",
  "plan": "yearly",
  "paid_at": "2026-08-19T23:50:00+07:00"
}
```

Chạy test:

```powershell
pytest -q
```

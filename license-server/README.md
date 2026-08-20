# TTS License Server

FastAPI server cho luồng thanh toán thử nghiệm và cấp license GPHI TTS. Server lưu
order bằng SQLite, gửi QR mẫu qua SMTP, tự giả lập thanh toán thành công, tái sử
dụng chữ ký Ed25519 hiện có và gửi License Key qua email.

Đây chỉ là **test flow**: chưa có webhook ngân hàng, xác nhận giao dịch thật,
VietQR production, cổng thanh toán hay worker riêng.

## Cài đặt trên Windows PowerShell

```powershell
cd license-server
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Mở `.env` và cấu hình:

```dotenv
LICENSE_PRIVATE_KEY=YOUR_PRIVATE_KEY_HERE
SQLITE_PATH=orders.db

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-account@example.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=your-account@example.com
SMTP_USE_TLS=true
SMTP_USE_SSL=false
SMTP_TIMEOUT=30
```

Không commit `.env`, private key hoặc mật khẩu SMTP. Nếu dùng SMTP cổng 465, đặt
`SMTP_USE_SSL=true` và `SMTP_USE_TLS=false`.

Khởi chạy server:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Swagger: <http://127.0.0.1:8000/docs>

Health check: <http://127.0.0.1:8000/health>

## Test `POST /payment/request`

Trong Swagger, dùng payload:

```json
{
  "name": "Nguyen Van A",
  "email": "abc@gmail.com",
  "plan": "yearly",
  "price": 1990000,
  "mac": "F0:68:E3:C4:D1:A1"
}
```

API chỉ trả thông tin tiếp nhận, không trả License Key:

```json
{
  "success": true,
  "id_order": "TTS-A8F32K",
  "message": "Yêu cầu thanh toán đã được tiếp nhận. Vui lòng kiểm tra email."
}
```

Sau khi response được tạo, BackgroundTasks chạy một workflow liên tục:

```text
PENDING
  -> gửi email QR mẫu
PAID + paid_at
  -> generate_license() từ dữ liệu đã lưu của order
LICENSE_CREATED + expires_at + license_key
  -> gửi email License Key
LICENSE_SENT
```

Mọi bước sau khi tạo order chỉ nhận `id_order` rồi đọc lại dữ liệu từ SQLite.
Nếu gửi email License Key lỗi, order giữ trạng thái `LICENSE_CREATED` và key vẫn
được lưu; gọi lại workflow cho cùng order sẽ chỉ thử gửi lại email key.

QR mẫu encode nội dung:

```text
ORDER=<id_order>
AMOUNT=<price>
CONTENT=<id_order>
```

## Database

Bảng `orders` được tự tạo tại `SQLITE_PATH` với các cột:

```text
id, id_order (UNIQUE), name, email, plan, price, mac, status,
created_at, paid_at, expires_at, license_key
```

Các trạng thái hợp lệ: `PENDING`, `PAID`, `LICENSE_CREATED`, `LICENSE_SENT`.
Các timestamp được lưu theo ISO 8601 và có timezone.

## Endpoint tạo license hiện có

`POST /license/generate` vẫn hoạt động độc lập như trước. Payload mẫu:

```json
{
  "customer_name": "Test Customer",
  "email": "test@example.com",
  "mac": "F0:68:E3:C4:D1:A1",
  "plan": "yearly",
  "paid_at": "2026-08-19T23:50:00+07:00"
}
```

## Chạy test

```powershell
pytest -q
```

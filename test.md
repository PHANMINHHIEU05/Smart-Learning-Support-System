Terminal 1 - Spring Boot main backend:

cd /home/hiubeo/Documents/code/Smart-Learning-Support-System/spring-backend

# Spring Boot KHONG tu doc file .env.
# Neu ban da tao spring-backend/.env thi phai source no vao terminal truoc khi chay Maven.
# Khong paste secret len chat.
#
# Lay Supabase DB host/password trong:
# Supabase Dashboard -> Project Settings -> Database -> Connection string -> JDBC
#
# File .env nen co dang:
# SPRING_DATASOURCE_URL=jdbc:postgresql://db.xxxxxxxxxxxxx.supabase.co:5432/postgres
# SPRING_DATASOURCE_USERNAME=postgres
# SPRING_DATASOURCE_PASSWORD=mat_khau_database_that
# APP_SECURITY_JWT_ISSUER_URI=https://xxxxxxxxxxxxx.supabase.co/auth/v1
# APP_SECURITY_JWT_JWK_SET_URI=https://xxxxxxxxxxxxx.supabase.co/auth/v1/.well-known/jwks.json
# APP_INTERNAL_SERVICE_TOKEN=dev-internal-token
# AI_WORKER_BASE_URL=http://localhost:8000
# AI_WORKER_INTERNAL_TOKEN=dev-internal-token
#
# Neu password co ky tu dac biet, boc gia tri bang dau nhay don trong .env.
# Chuoi `xxxxxxxxxxxxx` trong vi du van la placeholder.
# Ban phai thay no bang Project Ref that cua Supabase, vi du `db.abcdefghijklmnop.supabase.co`.

if [[ -f .env ]]; then
  set -a
  source .env
  set +a
else
  echo "Chua thay spring-backend/.env. Hay tao file .env hoac export bien moi truong thu cong."
fi

if [[ -z "$SPRING_DATASOURCE_URL" || "$SPRING_DATASOURCE_URL" == *"<supabase-host>"* || "$SPRING_DATASOURCE_PASSWORD" == *"<supabase-db-password>"* ]]; then
  echo "Spring chua nhan duoc Supabase config that."
  echo "Kiem tra spring-backend/.env: SPRING_DATASOURCE_URL va SPRING_DATASOURCE_PASSWORD phai la gia tri that."
else
  mvn spring-boot:run
fi

Terminal 2 - FastAPI AI worker:

cd /home/hiubeo/Documents/code/Smart-Learning-Support-System/backend

# Venv FastAPI da co san o root project.
# Dung .venv310 vi no la Python 3.10; KHONG dung .venv vi no la Python 3.14.
source ../.venv310/bin/activate

# Chi chay dong nay khi bi loi thieu package.
# python -m pip install -r requirements.txt

export AI_WORKER_INTERNAL_TOKEN='dev-internal-token'
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

Terminal 3 - Frontend:

cd /home/hiubeo/Documents/code/Smart-Learning-Support-System/frontend
export NEXT_PUBLIC_API_URL='http://localhost:8000'
export NEXT_PUBLIC_SPRING_API_URL='http://localhost:8080'
npm run dev

Terminal 4, chỉ chạy một lần nếu monitoring chưa cài đủ:

cd /home/hiubeo/Documents/code/Smart-Learning-Support-System/frontend/src/features/monitoring
./venv/bin/python -m pip install -r requirements.txt
./venv/bin/python -m pip install httpx

Sau khi chạy đủ:

- Web app: http://localhost:3000
- Spring Boot: http://localhost:8080/api/v1/health
- FastAPI: http://localhost:8000/health
- Vocabulary page: http://localhost:3000/vocab
- Review page: http://localhost:3000/vocab/review

Firefox extension:

1. Mo Firefox: about:debugging#/runtime/this-firefox
2. Bam Load Temporary Add-on
3. Chon file:
   /home/hiubeo/Documents/code/Smart-Learning-Support-System/firefox-extension/vocab-lookup/manifest.json
4. Vao http://localhost:3000/vocab
5. Bam Create Pairing Code
6. Mo popup extension, nhap pairing code, bam Pair
7. Chon tu tieng Anh tren web bat ky, bam Lookup roi Save Word

Neu bi loi "AI processing: No recent AI signal":

- Khong dung .venv Python 3.14 de chay backend.
- Backend FastAPI phai chay bang Python 3.10: `source ../.venv310/bin/activate`.
- FastAPI AI worker phai dang chay o port 8000.
- Spring Boot phai co AI_WORKER_BASE_URL='http://localhost:8000'.

Nếu camera không hiện
Chạy các lệnh này để kiểm tra:
ls -l /dev/video\*
cd /home/hiubeo/Documents/code/Smart-Learning-Support-System/frontend/src/features/monitoring
./venv/bin/python -c "import cv2; cap = cv2.VideoCapture(0); print('OK' if cap.isOpened() else 'FAIL'); cap.release()"

Nếu extension không Pair được:

- Restart Spring Boot de Flyway apply V7.
- Reload temporary add-on trong Firefox.
- Tao pairing code moi, vi code cu het han sau 10 phut.
- Kiem tra popup dang tro toi Spring API URL: http://localhost:8080

Nếu Spring báo UnknownHostException: <supabase-host>:

- Nghia la Spring van dang nhan placeholder, khong phai gia tri that.
- Kiem tra file `spring-backend/.env`.
- Sau khi sua `.env`, tat terminal Spring cu, mo terminal moi hoac chay lai `source .env`.
- Khong dung dau `<` va `>` trong gia tri that.
- `(.venv)` la Python virtualenv, khong lien quan toi bien moi truong cua Spring Boot.

Nếu Spring báo UnknownHostException: db.xxxxxxxxxxxxx.supabase.co:

- Nghia la ban da thay `<supabase-host>` bang mot host mau khac, nhung van chua phai host that.
- Vao Supabase Dashboard -> Project Settings -> Database -> Connection string -> JDBC.
- Copy host that trong JDBC, khong tu go `xxxxxxxxxxxxx`.

Terminal 1 - Spring Boot main backend:

```bash
cd /home/hiubeo/Documents/code/Smart-Learning-Support-System/spring-backend
set -a
source ./.env
set +a
echo "Spring DB URL: $SPRING_DATASOURCE_URL"
mvn spring-boot:run
```

Nếu dùng Supabase pooler port `6543`, Spring đã tắt PostgreSQL prepared statements qua Hikari `prepareThreshold=0`.

Terminal 2 - FastAPI AI worker:

```bash
cd /home/hiubeo/Documents/code/Smart-Learning-Support-System/backend
source ../.venv310/bin/activate
export AI_WORKER_INTERNAL_TOKEN='dev-internal-token'
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

De nguon tu dien/phat am chuan hon cho hoc tieng Anh:

- Dang ky API key tai Merriam-Webster Developer Center.
- Dien vao `backend/.env`:
  `MERRIAM_WEBSTER_LEARNERS_API_KEY=key_cua_ban`
- Restart FastAPI.
- Khi co key, FastAPI uu tien Merriam-Webster Learner's Dictionary cho definition, part of speech, phonetic va audio.
- Neu chua co key, he thong van fallback sang Free Dictionary API va MyMemory.

Terminal 3 - Frontend:

```bash
cd /home/hiubeo/Documents/code/Smart-Learning-Support-System/frontend
set -a
source ./.env.local
set +a
export NEXT_PUBLIC_API_URL='http://localhost:8000'
export NEXT_PUBLIC_SPRING_API_URL='http://localhost:8080'
npm run dev
```

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

Firefox extension local-only:

1. Mo Firefox.
2. Nhap vao thanh dia chi:
   `about:debugging#/runtime/this-firefox`
3. Bam `Load Temporary Add-on...`.
4. Chon file:
   /home/hiubeo/Documents/code/Smart-Learning-Support-System/firefox-extension/vocab-lookup/manifest.json
5. Neu Firefox hien icon extension tren toolbar, bam icon do. Neu chua thay, bam nut Extensions tren toolbar roi pin extension.
6. Sau khi load/reload extension, refresh lai trang web dang muon boi den tu.
7. Mo mot trang web bat ky co tieng Anh.
8. Boi den mot tu tieng Anh, bam icon extension.
9. Popup se tu hien nghia tieng Viet, phien am, dinh nghia tieng Anh va nut `Listen` phat am, khong can login/pair.
10. Nut `Listen` nam ngay canh o `Selected word`, bam la nghe phat am ngay ca khi chua luu tu.
11. Bam `Save Word` de luu local vao Firefox extension storage, khong can tai khoan/login.
12. Cach nhanh hon: boi den tu, chuot phai, chon `SLSS: Save selected word locally`.
13. Neu muon sua truoc khi luu: boi den tu, chuot phai, chon `SLSS: Open selected word in popup`.

Neu popup khong hien nghia/phat am:

- Reload temporary add-on trong `about:debugging#/runtime/this-firefox`.
- Refresh lai trang web dang boi den tu, roi boi den lai.
- Thu tren trang web binh thuong, khong thu tren `about:*`, trang extension noi bo, PDF viewer, hoac trang dac biet cua Firefox.
- Thu tu pho bien nhu `hello`, `result`, `consequence`, `resilient` de kiem tra audio.
- Extension co fallback truc tiep sang Free Dictionary API va MyMemory; neu backend AI loi tam thoi thi popup van co the hien nghia/phien am.

Luu y: extension dang la Temporary Add-on, nen moi lan tat/mo lai Firefox co the phai load lai `manifest.json`.

Dong goi Firefox extension local:

```bash
cd /home/hiubeo/Documents/code/Smart-Learning-Support-System
bash firefox-extension/vocab-lookup/package-firefox-extension.sh
```

File tao ra:

```text
/home/hiubeo/Documents/code/Smart-Learning-Support-System/dist/firefox/slss-vocabulary-lookup-0.1.0.xpi
```

Luu y: file `.xpi` local nay de test/dev. Muon cai nhu extension chinh thuc tren Firefox ban thuong thi can ky extension qua Mozilla.

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
- Neu web bao 401, Spring dang khong cong nhan token dang nhap. Kiem tra `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `APP_SECURITY_JWT_SECRET` trong `spring-backend/.env`, sau do restart Spring.
- Neu web bao frontend khong lay duoc access token, kiem tra `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` trong terminal frontend, sau do restart `npm run dev` va dang nhap lai.

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

Nếu Spring báo password/authentication failed:

- Kiem tra `SPRING_DATASOURCE_PASSWORD`.
- Neu FastAPI `DATABASE_URL` co `%40`, Spring password phai co ky tu `@`.
- Neu password co ky tu dac biet, boc bang dau nhay don trong `.env`.

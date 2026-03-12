# 📘 HƯỚNG DẪN CHI TIẾT — Xây dựng Backend FastAPI

> **Mục đích**: Tài liệu hướng dẫn từng bước xây dựng backend cho Smart Learning Support System.
> Mỗi phần gồm: **Giải thích flow → Mã giả (pseudocode) → Code thực tế**.

---

## 📋 Mục lục

1. [Tổng quan kiến trúc](#1-tổng-quan-kiến-trúc)
2. [Cấu trúc thư mục](#2-cấu-trúc-thư-mục)
3. [PHẦN A — Core: Config & Security](#3-phần-a--core-config--security)
4. [PHẦN B — Database Layer](#4-phần-b--database-layer)
5. [PHẦN C — Models (SQLAlchemy ORM)](#5-phần-c--models-sqlalchemy-orm)
6. [PHẦN D — Schemas (Pydantic v2)](#6-phần-d--schemas-pydantic-v2)
7. [PHẦN E — Services Layer (Business Logic)](#7-phần-e--services-layer-business-logic)
8. [PHẦN F — Routers (API Endpoints)](#8-phần-f--routers-api-endpoints)
9. [PHẦN G — Main Application (main.py)](#9-phần-g--main-application-mainpy)
10. [PHẦN H — Chạy & Test](#10-phần-h--chạy--test)

---

## 1. Tổng quan kiến trúc

### 1.1 Clean Architecture — 3 lớp

```
Request → Router → Service → Database
                     ↓
              Business Logic
              Validation
              Alert Evaluation
```

**Nguyên tắc:**

- **Router** (controller): Chỉ parse request, gọi service, trả response. KHÔNG có logic.
- **Service**: Chứa toàn bộ business logic (validate, tính toán, query phức tạp).
- **DB Layer**: AsyncSession + raw SQLAlchemy query. Không ORM relationship phức tạp.

### 1.2 Flow xác thực (Authentication)

```
Client gửi request
    ↓
Header: Authorization: Bearer <jwt_token>
    ↓
FastAPI Dependency: get_current_user()
    ↓
Decode JWT bằng SUPABASE_JWT_SECRET (thuật toán HS256)
    ↓
Lấy claim "sub" → đây chính là user_id (UUID)
    ↓
Trả về user_id cho router
    ↓
Router truyền user_id vào service
    ↓
Service dùng user_id để filter query (WHERE user_id = ?)
```

**Tại sao không dùng service_role_key?**

- Service role key bypass RLS → nguy hiểm.
- JWT secret chỉ verify token, query vẫn chạy với quyền user → RLS vẫn hoạt động.

### 1.3 Flow dữ liệu ví dụ — Tạo Task

```
POST /api/v1/tasks  +  Bearer token
    ↓
[Router: tasks.py]
  1. get_current_user() → user_id
  2. Parse body → TaskCreate schema
  3. Gọi task_service.create_task(db, user_id, data)
    ↓
[Service: task_service.py]
  1. Tạo Task model instance
  2. Gán user_id, created_at, updated_at
  3. db.add(task) → flush
  4. Return task
    ↓
[Router]
  5. Return TaskResponse (Pydantic serialize từ ORM model)
```

---

## 2. Cấu trúc thư mục

```
backend/
├── app/
│   ├── __init__.py              ← Package marker (file rỗng)
│   │
│   ├── main.py                  ← Entry point: tạo FastAPI app, đăng ký middleware, router
│   │
│   ├── core/                    ← Cấu hình & bảo mật
│   │   ├── __init__.py
│   │   ├── config.py            ← Đọc .env → class Settings (Pydantic Settings)
│   │   ├── security.py          ← Decode JWT, dependency get_current_user
│   │   ├── exceptions.py        ← Global exception handlers
│   │   └── logging_config.py    ← Setup logging format
│   │
│   ├── db/                      ← Database connection
│   │   ├── __init__.py
│   │   └── session.py           ← Async engine + session factory + dependency get_db
│   │
│   ├── models/                  ← SQLAlchemy ORM models (map bảng đã có)
│   │   ├── __init__.py          ← Export tất cả models
│   │   ├── base.py              ← DeclarativeBase
│   │   ├── user.py
│   │   ├── user_setting.py
│   │   ├── task.py
│   │   ├── study_session.py
│   │   ├── session_block.py
│   │   ├── ai_event.py
│   │   ├── alert_rule.py
│   │   └── alert.py
│   │
│   ├── schemas/                 ← Pydantic v2 schemas (request/response)
│   │   ├── __init__.py
│   │   ├── task.py              ← TaskCreate, TaskUpdate, TaskResponse
│   │   ├── study_session.py     ← SessionCreate, SessionEnd, SessionResponse
│   │   ├── session_block.py     ← BlockCreate, BlockResponse
│   │   ├── ai_event.py          ← AiEventCreate, AiEventBatchCreate, AiEventResponse
│   │   ├── alert_rule.py        ← AlertRuleCreate, AlertRuleUpdate, AlertRuleResponse
│   │   ├── alert.py             ← AlertResponse
│   │   └── analytics.py         ← DailySummary
│   │
│   ├── services/                ← Business logic
│   │   ├── __init__.py
│   │   ├── task_service.py
│   │   ├── session_service.py
│   │   ├── block_service.py
│   │   ├── ai_event_service.py
│   │   ├── alert_service.py
│   │   └── analytics_service.py
│   │
│   └── routers/                 ← API endpoints
│       ├── __init__.py
│       ├── tasks.py
│       ├── sessions.py
│       ├── blocks.py
│       ├── ai_events.py
│       ├── alerts.py
│       └── analytics.py
│
├── requirements.txt             ← ✅ Đã cài
├── .env.example                 ← ✅ Đã tạo
├── .env                         ← Bạn tự tạo (copy từ .env.example)
├── venv/                        ← ✅ Đã tạo
├── Dockerfile                   ← (Tạo sau nếu cần deploy)
└── GUIDE.md                     ← File này
```

---

## 3. PHẦN A — Core: Config & Security

### 3.1 `app/core/config.py` — Đọc biến môi trường

**Flow:**

```
.env file → Pydantic Settings tự đọc → class Settings → singleton `settings`
Toàn bộ app import `settings` từ đây, KHÔNG bao giờ dùng os.environ trực tiếp
```

**Mã giả:**

```
class Settings:
    DATABASE_URL: string         # connection string asyncpg
    SUPABASE_JWT_SECRET: string  # để verify JWT
    SUPABASE_URL: string         # URL project Supabase
    CORS_ORIGINS: string         # "http://localhost:3000,..."
    DEBUG: boolean

    method cors_origins_list():
        return split CORS_ORIGINS by ","

settings = Settings()  # tạo 1 lần, dùng mãi
```

**Code:**

```python
# app/core/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Database ──
    DATABASE_URL: str

    # ── Supabase Auth ──
    SUPABASE_JWT_SECRET: str
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""

    # ── App ──
    APP_NAME: str = "Smart Learning Support System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # ── CORS ──
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # ── Server ──
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
```

---

### 3.2 `app/core/security.py` — Xác thực JWT

**Flow chi tiết:**

```
1. FastAPI tự lấy header Authorization: Bearer <token>
   → HTTPBearer() dependency parse ra token string

2. _decode_jwt(token):
   → Dùng python-jose để decode
   → Thuật toán: HS256
   → Secret: SUPABASE_JWT_SECRET
   → Không verify audience (Supabase không bắt buộc)
   → Nếu token sai/hết hạn → 401 Unauthorized

3. get_current_user(credentials):
   → Gọi _decode_jwt()
   → Lấy payload["sub"] → đây là auth.users.id (UUID)
   → Convert sang uuid.UUID
   → Trả về cho router dùng
```

**Mã giả:**

```
function decode_jwt(token):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithm="HS256")
        return payload
    catch:
        throw 401 "Token không hợp lệ"

function get_current_user(authorization_header):
    token = extract from header
    payload = decode_jwt(token)
    user_id = payload["sub"]
    if user_id is None:
        throw 401 "Missing sub claim"
    return UUID(user_id)
```

**Code:**

```python
# app/core/security.py

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import settings

_bearer_scheme = HTTPBearer()


def _decode_jwt(token: str) -> dict:
    """Giải mã & xác thực JWT bằng Supabase JWT secret (HS256)."""
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
        return payload
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token không hợp lệ: {exc}",
        ) from exc


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer_scheme)],
) -> uuid.UUID:
    """
    Dependency — trả về user_id (UUID) đã xác thực.

    Dùng trong router:
        @router.get("/me")
        async def me(user_id: uuid.UUID = Depends(get_current_user)):
            ...
    """
    payload = _decode_jwt(credentials.credentials)
    sub = payload.get("sub")
    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token thiếu claim 'sub'",
        )
    try:
        return uuid.UUID(sub)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Claim 'sub' không phải UUID hợp lệ",
        ) from exc
```

---

### 3.3 `app/core/exceptions.py` — Global Exception Handler

**Flow:**

```
Bất kỳ exception nào không được catch trong router/service
    ↓
FastAPI gọi exception handler tương ứng
    ↓
Trả về JSON response thống nhất: {"detail": "..."}
    ↓
3 loại:
  - HTTPException → trả status code + detail gốc
  - ValueError → 422 Unprocessable Entity
  - Exception (catch-all) → 500 + log traceback, KHÔNG lộ chi tiết cho client
```

**Code:**

```python
# app/core/exceptions.py

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("app")


def register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        return JSONResponse(
            status_code=422,
            content={"detail": str(exc)},
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )
```

---

### 3.4 `app/core/logging_config.py` — Cấu hình Logging

**Code:**

```python
# app/core/logging_config.py

import logging
import sys

from app.core.config import settings


def setup_logging() -> None:
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Giảm noise
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.DEBUG else logging.WARNING
    )
```

---

### 3.5 `app/core/__init__.py`

```python
# app/core/__init__.py
# File rỗng — chỉ đánh dấu đây là Python package
```

---

## 4. PHẦN B — Database Layer

### 4.1 `app/db/session.py` — Async Engine & Session

**Flow:**

```
App khởi động
    ↓
Tạo 1 async engine (singleton) kết nối PostgreSQL qua asyncpg
    ↓
Tạo session factory (async_sessionmaker)
    ↓
Mỗi API request:
    → FastAPI gọi dependency get_db()
    → Yield 1 AsyncSession
    → Request xong → auto commit
    → Có exception → auto rollback
    → Session tự đóng
```

**Tại sao dùng asyncpg?**

- asyncpg là driver async nhanh nhất cho PostgreSQL.
- SQLAlchemy 2.0 hỗ trợ async native qua `create_async_engine`.

**Mã giả:**

```
engine = create_async_engine(DATABASE_URL, pool_size=5)
session_factory = async_sessionmaker(engine)

function get_db():
    session = session_factory()
    try:
        yield session       # request dùng session
        session.commit()    # thành công → commit
    except:
        session.rollback()  # lỗi → rollback
    finally:
        session.close()
```

**Code:**

```python
# app/db/session.py

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,        # True → log SQL queries
    pool_size=5,                # Connection pool tối thiểu
    max_overflow=10,            # Thêm tối đa 10 connection khi đông
    pool_pre_ping=True,         # Kiểm tra connection còn sống
    pool_recycle=300,           # Tái tạo connection mỗi 5 phút
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,     # Không expire attributes sau commit
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency — cung cấp AsyncSession.

    Router dùng:
        @router.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

### 4.2 `app/db/__init__.py`

```python
# app/db/__init__.py
# File rỗng
```

---

## 5. PHẦN C — Models (SQLAlchemy ORM)

### 5.1 Nguyên tắc quan trọng

```
⚠️  KHÔNG dùng Base.metadata.create_all()
⚠️  Bảng ĐÃ tồn tại trên Supabase
⚠️  Model chỉ MAP đến bảng hiện có, không tạo mới
⚠️  Dùng mapped_column() style SQLAlchemy 2.0
```

### 5.2 `app/models/base.py`

```python
# app/models/base.py

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

### 5.3 `app/models/user.py` — Bảng users

**Map đến:**

```sql
-- Supabase: public.users
-- user_id = auth.users.id (UUID, đồng bộ bởi Supabase trigger)
```

**Code:**

```python
# app/models/user.py

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    display_name: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
```

### 5.4 `app/models/user_setting.py`

```python
# app/models/user_setting.py

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Integer, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class UserSetting(Base):
    __tablename__ = "user_settings"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    timezone: Mapped[str | None] = mapped_column(String, nullable=True)
    daily_goal_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pomodoro_focus_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pomodoro_break_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pomodoro_long_break_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pomodoro_cycles_before_long_break: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ai_monitoring_enabled: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    retention_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
```

### 5.5 `app/models/task.py`

```python
# app/models/task.py

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Integer, String, Text, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Task(Base):
    __tablename__ = "tasks"

    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="todo")
    priority: Mapped[int | None] = mapped_column(Integer, nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    estimated_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    subject_name: Mapped[str | None] = mapped_column(String, nullable=True)
    tags_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
```

### 5.6 `app/models/study_session.py`

```python
# app/models/study_session.py

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class StudySession(Base):
    __tablename__ = "study_sessions"

    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    task_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    planned_mode: Mapped[str | None] = mapped_column(String, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
```

### 5.7 `app/models/session_block.py`

```python
# app/models/session_block.py

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SessionBlock(Base):
    __tablename__ = "session_blocks"

    block_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    block_type: Mapped[str] = mapped_column(String, nullable=False)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

### 5.8 `app/models/ai_event.py`

```python
# app/models/ai_event.py

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Float, Integer, String, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AiEvent(Base):
    __tablename__ = "ai_events"

    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    session_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    severity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
```

### 5.9 `app/models/alert_rule.py`

```python
# app/models/alert_rule.py

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Integer, String, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AlertRule(Base):
    __tablename__ = "alert_rules"

    rule_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    trigger_event_type: Mapped[str] = mapped_column(String, nullable=False)
    cooldown_seconds: Mapped[int] = mapped_column(Integer, default=60)
    condition_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    action_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
```

### 5.10 `app/models/alert.py`

```python
# app/models/alert.py

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Alert(Base):
    __tablename__ = "alerts"

    alert_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    session_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    rule_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    event_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    fired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    channel: Mapped[str | None] = mapped_column(String, nullable=True)
    message: Mapped[str | None] = mapped_column(String, nullable=True)
    payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
```

### 5.11 `app/models/__init__.py` — Export

```python
# app/models/__init__.py

from app.models.base import Base
from app.models.user import User
from app.models.user_setting import UserSetting
from app.models.task import Task
from app.models.study_session import StudySession
from app.models.session_block import SessionBlock
from app.models.ai_event import AiEvent
from app.models.alert_rule import AlertRule
from app.models.alert import Alert
```

---

## 6. PHẦN D — Schemas (Pydantic v2)

### 6.1 Nguyên tắc

```
Schema = Pydantic model dùng cho:
  - Validate request body (Create, Update)
  - Serialize response (Response)

Quy ước đặt tên:
  - XxxCreate  → cho POST body
  - XxxUpdate  → cho PATCH body (tất cả fields optional)
  - XxxResponse → cho response (có from_attributes=True để đọc từ ORM model)
```

### 6.2 `app/schemas/task.py`

**Giải thích:**

- `TaskCreate`: client gửi khi tạo task mới. `title` bắt buộc, `status` mặc định "todo".
- `TaskUpdate`: client gửi khi update. Tất cả optional (chỉ gửi field muốn sửa).
- `TaskResponse`: app trả về. `from_attributes=True` cho phép Pydantic đọc attribute từ SQLAlchemy model.

```python
# app/schemas/task.py

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    status: str = Field(default="todo", pattern=r"^(todo|doing|done|archived)$")
    priority: int | None = Field(default=None, ge=0, le=10)
    due_at: datetime | None = None
    estimated_minutes: int | None = Field(default=None, ge=1)
    subject_name: str | None = None
    tags_json: Any | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    status: str | None = Field(default=None, pattern=r"^(todo|doing|done|archived)$")
    priority: int | None = Field(default=None, ge=0, le=10)
    due_at: datetime | None = None
    estimated_minutes: int | None = Field(default=None, ge=1)
    subject_name: str | None = None
    tags_json: Any | None = None


class TaskResponse(BaseModel):
    task_id: uuid.UUID
    user_id: uuid.UUID
    title: str
    description: str | None = None
    status: str
    priority: int | None = None
    due_at: datetime | None = None
    estimated_minutes: int | None = None
    subject_name: str | None = None
    tags_json: Any | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
```

### 6.3 `app/schemas/study_session.py`

```python
# app/schemas/study_session.py

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    task_id: uuid.UUID | None = None
    planned_mode: str | None = Field(default=None, pattern=r"^(pomodoro|free)$")
    started_at: datetime
    notes: str | None = None


class SessionEnd(BaseModel):
    ended_at: datetime
    end_reason: str = Field(default="completed", pattern=r"^(completed|stopped|timeout|error)$")
    notes: str | None = None


class SessionResponse(BaseModel):
    session_id: uuid.UUID
    user_id: uuid.UUID
    task_id: uuid.UUID | None = None
    planned_mode: str | None = None
    started_at: datetime
    ended_at: datetime | None = None
    end_reason: str | None = None
    notes: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
```

### 6.4 `app/schemas/session_block.py`

```python
# app/schemas/session_block.py

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class BlockCreate(BaseModel):
    session_id: uuid.UUID
    block_type: str = Field(..., pattern=r"^(focus|break|long_break)$")
    start_at: datetime
    end_at: datetime | None = None


class BlockResponse(BaseModel):
    block_id: uuid.UUID
    session_id: uuid.UUID
    block_type: str
    start_at: datetime
    end_at: datetime | None = None

    model_config = {"from_attributes": True}
```

### 6.5 `app/schemas/ai_event.py`

**Giải thích validation:**

- `confidence` phải từ 0.0 đến 1.0 (xác suất AI).
- `end_at >= start_at` (validator tự kiểm tra).
- `AiEventBatchCreate` cho phép gửi tối đa 500 events 1 lần.

```python
# app/schemas/ai_event.py

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator


class AiEventCreate(BaseModel):
    session_id: uuid.UUID | None = None
    event_type: str = Field(..., min_length=1)
    start_at: datetime
    end_at: datetime | None = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    severity: int | None = Field(default=None, ge=1, le=10)
    payload_json: Any | None = None

    @model_validator(mode="after")
    def validate_time_range(self):
        if self.end_at is not None and self.start_at is not None:
            if self.end_at < self.start_at:
                raise ValueError("end_at phải >= start_at")
        return self


class AiEventBatchCreate(BaseModel):
    events: list[AiEventCreate] = Field(..., min_length=1, max_length=500)


class AiEventResponse(BaseModel):
    event_id: uuid.UUID
    user_id: uuid.UUID
    session_id: uuid.UUID | None = None
    event_type: str
    start_at: datetime
    end_at: datetime | None = None
    confidence: float
    severity: int | None = None
    payload_json: Any | None = None

    model_config = {"from_attributes": True}
```

### 6.6 `app/schemas/alert_rule.py`

```python
# app/schemas/alert_rule.py

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AlertRuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    is_enabled: bool = True
    trigger_event_type: str = Field(..., min_length=1)
    cooldown_seconds: int = Field(default=60, ge=0)
    condition_json: Any | None = None
    action_json: Any | None = None


class AlertRuleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    is_enabled: bool | None = None
    trigger_event_type: str | None = None
    cooldown_seconds: int | None = Field(default=None, ge=0)
    condition_json: Any | None = None
    action_json: Any | None = None


class AlertRuleResponse(BaseModel):
    rule_id: uuid.UUID
    user_id: uuid.UUID
    name: str
    is_enabled: bool
    trigger_event_type: str
    cooldown_seconds: int
    condition_json: Any | None = None
    action_json: Any | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
```

### 6.7 `app/schemas/alert.py`

```python
# app/schemas/alert.py

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AlertResponse(BaseModel):
    alert_id: uuid.UUID
    user_id: uuid.UUID
    session_id: uuid.UUID | None = None
    rule_id: uuid.UUID | None = None
    event_id: uuid.UUID | None = None
    fired_at: datetime
    channel: str | None = None
    message: str | None = None
    payload_json: Any | None = None

    model_config = {"from_attributes": True}
```

### 6.8 `app/schemas/analytics.py`

```python
# app/schemas/analytics.py

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class DailySummary(BaseModel):
    date: date
    total_focus_seconds: int = 0
    total_break_seconds: int = 0
    distraction_count: int = 0
    fatigue_count: int = 0
    session_count: int = 0
```

### 6.9 `app/schemas/__init__.py`

```python
# app/schemas/__init__.py
# File rỗng hoặc import tất cả
```

---

## 7. PHẦN E — Services Layer (Business Logic)

### 7.1 Pattern chung

Mỗi service là 1 module chứa **async functions** thuần. Nhận `db: AsyncSession` + `user_id: UUID` + data.

```
Service function pattern:
    async def do_something(db: AsyncSession, user_id: UUID, data: Schema) -> Model:
        1. Validate business rules
        2. Build SQL query (luôn filter by user_id)
        3. Execute query
        4. Return result
```

---

### 7.2 `app/services/task_service.py`

**Flow — Create Task:**

```
Input: db, user_id, TaskCreate
    ↓
Tạo Task model:
    task_id = uuid4()
    user_id = user_id (từ JWT)
    các field từ TaskCreate
    created_at = now()
    updated_at = now()
    ↓
db.add(task)
db.flush()  ← ghi vào DB nhưng chưa commit (commit ở get_db)
    ↓
Return task
```

**Flow — List Tasks (có pagination + filter):**

```
Input: db, user_id, status?, due_from?, due_to?, offset, limit
    ↓
SELECT * FROM tasks WHERE user_id = ?
    AND (status = ? IF provided)
    AND (due_at >= due_from IF provided)
    AND (due_at <= due_to IF provided)
ORDER BY created_at DESC
OFFSET ? LIMIT ?
    ↓
Return list[Task]
```

**Flow — Update Task:**

```
Input: db, user_id, task_id, TaskUpdate
    ↓
SELECT task WHERE task_id = ? AND user_id = ?
    ↓
Nếu không tìm thấy → 404
    ↓
Chỉ update những field != None trong TaskUpdate
    updated_at = now()
    ↓
Return updated task
```

**Flow — Delete Task:**

```
Input: db, user_id, task_id
    ↓
DELETE FROM tasks WHERE task_id = ? AND user_id = ?
    ↓
Nếu rowcount == 0 → 404
```

**Code:**

```python
# app/services/task_service.py

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate


async def create_task(
    db: AsyncSession, user_id: uuid.UUID, data: TaskCreate
) -> Task:
    now = datetime.now(timezone.utc)
    task = Task(
        task_id=uuid.uuid4(),
        user_id=user_id,
        **data.model_dump(),
        created_at=now,
        updated_at=now,
    )
    db.add(task)
    await db.flush()
    return task


async def get_task(
    db: AsyncSession, user_id: uuid.UUID, task_id: uuid.UUID
) -> Task:
    stmt = select(Task).where(Task.task_id == task_id, Task.user_id == user_id)
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


async def list_tasks(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    status_filter: str | None = None,
    due_from: datetime | None = None,
    due_to: datetime | None = None,
    offset: int = 0,
    limit: int = 20,
) -> list[Task]:
    stmt = select(Task).where(Task.user_id == user_id)

    if status_filter:
        stmt = stmt.where(Task.status == status_filter)
    if due_from:
        stmt = stmt.where(Task.due_at >= due_from)
    if due_to:
        stmt = stmt.where(Task.due_at <= due_to)

    stmt = stmt.order_by(Task.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_task(
    db: AsyncSession, user_id: uuid.UUID, task_id: uuid.UUID, data: TaskUpdate
) -> Task:
    task = await get_task(db, user_id, task_id)

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(task, key, value)

    task.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return task


async def delete_task(
    db: AsyncSession, user_id: uuid.UUID, task_id: uuid.UUID
) -> None:
    stmt = delete(Task).where(Task.task_id == task_id, Task.user_id == user_id)
    result = await db.execute(stmt)
    if result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
```

---

### 7.3 `app/services/session_service.py`

**Flow — Create Session:**

```
Input: db, user_id, SessionCreate
    ↓
Tạo StudySession:
    session_id = uuid4()
    user_id = from JWT
    started_at = from body
    created_at = now()
    ↓
db.add → flush → return
```

**Flow — End Session:**

```
Input: db, user_id, session_id, SessionEnd
    ↓
SELECT session WHERE id = ? AND user_id = ?
    ↓
Validate: ended_at >= started_at (QUAN TRỌNG)
Validate: session chưa kết thúc (ended_at is NULL)
    ↓
Gán ended_at, end_reason
    ↓
Return updated session
```

**Code:**

```python
# app/services/session_service.py

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.study_session import StudySession
from app.schemas.study_session import SessionCreate, SessionEnd


async def create_session(
    db: AsyncSession, user_id: uuid.UUID, data: SessionCreate
) -> StudySession:
    session = StudySession(
        session_id=uuid.uuid4(),
        user_id=user_id,
        task_id=data.task_id,
        planned_mode=data.planned_mode,
        started_at=data.started_at,
        notes=data.notes,
        created_at=datetime.now(timezone.utc),
    )
    db.add(session)
    await db.flush()
    return session


async def get_session(
    db: AsyncSession, user_id: uuid.UUID, session_id: uuid.UUID
) -> StudySession:
    stmt = select(StudySession).where(
        StudySession.session_id == session_id,
        StudySession.user_id == user_id,
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session


async def end_session(
    db: AsyncSession, user_id: uuid.UUID, session_id: uuid.UUID, data: SessionEnd
) -> StudySession:
    session = await get_session(db, user_id, session_id)

    if session.ended_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session đã kết thúc rồi",
        )

    if data.ended_at < session.started_at:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ended_at phải >= started_at",
        )

    session.ended_at = data.ended_at
    session.end_reason = data.end_reason
    if data.notes is not None:
        session.notes = data.notes

    await db.flush()
    return session


async def list_sessions(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    offset: int = 0,
    limit: int = 20,
) -> list[StudySession]:
    stmt = select(StudySession).where(StudySession.user_id == user_id)

    if date_from:
        stmt = stmt.where(StudySession.started_at >= date_from)
    if date_to:
        stmt = stmt.where(StudySession.started_at <= date_to)

    stmt = stmt.order_by(StudySession.started_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())
```

---

### 7.4 `app/services/block_service.py`

**Flow — Add Block:**

```
Input: db, user_id, BlockCreate
    ↓
Verify session thuộc user_id (SELECT study_sessions WHERE session_id AND user_id)
    ↓
Validate chronological consistency:
    Lấy block cuối cùng của session (ORDER BY start_at DESC LIMIT 1)
    Nếu block cuối chưa có end_at → báo lỗi "Block trước chưa kết thúc"
    Nếu new block.start_at < last block.end_at → báo lỗi "Thời gian chồng chéo"
    ↓
INSERT session_blocks → return
```

**Code:**

```python
# app/services/block_service.py

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session_block import SessionBlock
from app.models.study_session import StudySession
from app.schemas.session_block import BlockCreate


async def _verify_session_ownership(
    db: AsyncSession, user_id: uuid.UUID, session_id: uuid.UUID
) -> StudySession:
    """Kiểm tra session có thuộc user không."""
    stmt = select(StudySession).where(
        StudySession.session_id == session_id,
        StudySession.user_id == user_id,
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session


async def create_block(
    db: AsyncSession, user_id: uuid.UUID, data: BlockCreate
) -> SessionBlock:
    # 1. Verify ownership
    await _verify_session_ownership(db, user_id, data.session_id)

    # 2. Validate chronological consistency
    stmt = (
        select(SessionBlock)
        .where(SessionBlock.session_id == data.session_id)
        .order_by(SessionBlock.start_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    last_block = result.scalar_one_or_none()

    if last_block is not None:
        if last_block.end_at is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Block trước chưa kết thúc (end_at is NULL). Hãy kết thúc block cũ trước.",
            )
        if data.start_at < last_block.end_at:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="start_at phải >= end_at của block trước (thời gian chồng chéo)",
            )

    # 3. Create
    block = SessionBlock(
        block_id=uuid.uuid4(),
        session_id=data.session_id,
        block_type=data.block_type,
        start_at=data.start_at,
        end_at=data.end_at,
    )
    db.add(block)
    await db.flush()
    return block


async def list_blocks_by_session(
    db: AsyncSession, user_id: uuid.UUID, session_id: uuid.UUID
) -> list[SessionBlock]:
    # Verify ownership first
    await _verify_session_ownership(db, user_id, session_id)

    stmt = (
        select(SessionBlock)
        .where(SessionBlock.session_id == session_id)
        .order_by(SessionBlock.start_at.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
```

---

### 7.5 `app/services/ai_event_service.py`

**Flow — Insert Single Event:**

```
Input: db, user_id, AiEventCreate
    ↓
Tạo AiEvent model (user_id từ JWT, KHÔNG từ body)
    ↓
INSERT → flush
    ↓
⭐ Gọi alert_service.evaluate_rules(db, user_id, event)
    → Kiểm tra alert_rules có match không
    → Nếu match → tạo alert record
    ↓
Return event
```

**Flow — Insert Batch:**

```
Input: db, user_id, AiEventBatchCreate (list events)
    ↓
Loop qua mỗi event:
    Tạo AiEvent model
    db.add(event)
    ↓
db.flush() (một lần cho tất cả)
    ↓
Loop qua mỗi event → evaluate_rules
    ↓
Return list events
```

**Code:**

```python
# app/services/ai_event_service.py

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_event import AiEvent
from app.schemas.ai_event import AiEventCreate, AiEventBatchCreate


async def create_event(
    db: AsyncSession, user_id: uuid.UUID, data: AiEventCreate
) -> AiEvent:
    event = AiEvent(
        event_id=uuid.uuid4(),
        user_id=user_id,
        session_id=data.session_id,
        event_type=data.event_type,
        start_at=data.start_at,
        end_at=data.end_at,
        confidence=data.confidence,
        severity=data.severity,
        payload_json=data.payload_json,
    )
    db.add(event)
    await db.flush()

    # Trigger alert evaluation (import ở đây để tránh circular import)
    from app.services.alert_service import evaluate_rules_for_event
    await evaluate_rules_for_event(db, user_id, event)

    return event


async def create_events_batch(
    db: AsyncSession, user_id: uuid.UUID, data: AiEventBatchCreate
) -> list[AiEvent]:
    events = []
    for item in data.events:
        event = AiEvent(
            event_id=uuid.uuid4(),
            user_id=user_id,
            session_id=item.session_id,
            event_type=item.event_type,
            start_at=item.start_at,
            end_at=item.end_at,
            confidence=item.confidence,
            severity=item.severity,
            payload_json=item.payload_json,
        )
        db.add(event)
        events.append(event)

    await db.flush()

    # Evaluate rules for each event
    from app.services.alert_service import evaluate_rules_for_event
    for event in events:
        await evaluate_rules_for_event(db, user_id, event)

    return events


async def list_events(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    event_type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    offset: int = 0,
    limit: int = 50,
) -> list[AiEvent]:
    stmt = select(AiEvent).where(AiEvent.user_id == user_id)

    if event_type:
        stmt = stmt.where(AiEvent.event_type == event_type)
    if date_from:
        stmt = stmt.where(AiEvent.start_at >= date_from)
    if date_to:
        stmt = stmt.where(AiEvent.start_at <= date_to)

    stmt = stmt.order_by(AiEvent.start_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())
```

---

### 7.6 `app/services/alert_service.py` ⭐ (Phức tạp nhất)

**Flow — Evaluate Rules khi có AI Event mới:**

```
Input: db, user_id, ai_event (vừa INSERT)
    ↓
1. SELECT alert_rules WHERE:
     user_id = ?
     is_enabled = true
     trigger_event_type = event.event_type
    ↓
2. For each matching rule:
     a. Check condition:
        - condition_json có minConfidence? → event.confidence >= minConfidence?
        - condition_json có minDurationSec? → (end_at - start_at) >= minDurationSec?
     b. Check cooldown:
        - SELECT MAX(fired_at) FROM alerts WHERE rule_id = ? AND user_id = ?
        - Nếu (now - last_fired_at) < cooldown_seconds → SKIP (chưa hết cooldown)
     c. Nếu pass cả 2:
        - INSERT INTO alerts (alert_id, user_id, session_id, rule_id, event_id,
          fired_at, channel, message, payload_json)
    ↓
3. Return (void — side effect)
```

**Sơ đồ quyết định:**

```
Event: POSTURE_SLOUCH, confidence=0.87
    ↓
Rule: trigger=POSTURE_SLOUCH, condition={minConfidence: 0.6}, cooldown=60s
    ↓
├─ confidence 0.87 >= 0.6? ✅
├─ last alert > 60s ago?   ✅
└─ → INSERT alert: "Bạn đang gù lưng!"
```

**Code:**

```python
# app/services/alert_service.py

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_event import AiEvent
from app.models.alert import Alert
from app.models.alert_rule import AlertRule
from app.schemas.alert_rule import AlertRuleCreate, AlertRuleUpdate

logger = logging.getLogger("app.alert_service")


# ────────────────────────── CRUD Alert Rules ──────────────────────────

async def create_rule(
    db: AsyncSession, user_id: uuid.UUID, data: AlertRuleCreate
) -> AlertRule:
    rule = AlertRule(
        rule_id=uuid.uuid4(),
        user_id=user_id,
        **data.model_dump(),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(rule)
    await db.flush()
    return rule


async def get_rule(
    db: AsyncSession, user_id: uuid.UUID, rule_id: uuid.UUID
) -> AlertRule:
    stmt = select(AlertRule).where(AlertRule.rule_id == rule_id, AlertRule.user_id == user_id)
    result = await db.execute(stmt)
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert rule not found")
    return rule


async def list_rules(
    db: AsyncSession, user_id: uuid.UUID
) -> list[AlertRule]:
    stmt = select(AlertRule).where(AlertRule.user_id == user_id).order_by(AlertRule.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_rule(
    db: AsyncSession, user_id: uuid.UUID, rule_id: uuid.UUID, data: AlertRuleUpdate
) -> AlertRule:
    rule = await get_rule(db, user_id, rule_id)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(rule, key, value)
    rule.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return rule


async def delete_rule(
    db: AsyncSession, user_id: uuid.UUID, rule_id: uuid.UUID
) -> None:
    stmt = delete(AlertRule).where(AlertRule.rule_id == rule_id, AlertRule.user_id == user_id)
    result = await db.execute(stmt)
    if result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert rule not found")


# ────────────────────────── List Alerts ──────────────────────────

async def list_alerts(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    session_id: uuid.UUID | None = None,
    offset: int = 0,
    limit: int = 50,
) -> list[Alert]:
    stmt = select(Alert).where(Alert.user_id == user_id)
    if session_id:
        stmt = stmt.where(Alert.session_id == session_id)
    stmt = stmt.order_by(Alert.fired_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ────────────────────────── Rule Evaluation Engine ──────────────────────────

async def evaluate_rules_for_event(
    db: AsyncSession, user_id: uuid.UUID, event: AiEvent
) -> None:
    """
    Được gọi SAU KHI insert ai_event.
    Tìm tất cả alert_rules match → check condition → check cooldown → fire alert.
    """
    # 1. Lấy rules match event_type
    stmt = select(AlertRule).where(
        AlertRule.user_id == user_id,
        AlertRule.is_enabled == True,
        AlertRule.trigger_event_type == event.event_type,
    )
    result = await db.execute(stmt)
    rules = result.scalars().all()

    now = datetime.now(timezone.utc)

    for rule in rules:
        # 2a. Check condition_json
        if not _check_condition(rule, event):
            logger.debug("Rule %s: condition không match", rule.rule_id)
            continue

        # 2b. Check cooldown
        if not await _check_cooldown(db, user_id, rule, now):
            logger.debug("Rule %s: đang trong cooldown", rule.rule_id)
            continue

        # 2c. Fire alert!
        alert = Alert(
            alert_id=uuid.uuid4(),
            user_id=user_id,
            session_id=event.session_id,
            rule_id=rule.rule_id,
            event_id=event.event_id,
            fired_at=now,
            channel=_get_channel(rule),
            message=f"[{rule.name}] Phát hiện: {event.event_type}",
            payload_json=rule.action_json,
        )
        db.add(alert)
        logger.info("🔔 Alert fired: rule=%s, event=%s", rule.name, event.event_type)

    await db.flush()


def _check_condition(rule: AlertRule, event: AiEvent) -> bool:
    """Kiểm tra condition_json có match với event không."""
    cond = rule.condition_json
    if not cond or not isinstance(cond, dict):
        return True  # không có condition → luôn match

    # Check minConfidence
    min_conf = cond.get("minConfidence")
    if min_conf is not None and event.confidence < min_conf:
        return False

    # Check minDurationSec
    min_dur = cond.get("minDurationSec")
    if min_dur is not None:
        if event.end_at is None or event.start_at is None:
            return False
        duration = (event.end_at - event.start_at).total_seconds()
        if duration < min_dur:
            return False

    return True


async def _check_cooldown(
    db: AsyncSession, user_id: uuid.UUID, rule: AlertRule, now: datetime
) -> bool:
    """
    Kiểm tra đã qua cooldown chưa.
    Return True nếu OK (đã qua cooldown hoặc chưa có alert nào).
    """
    if rule.cooldown_seconds <= 0:
        return True

    stmt = select(func.max(Alert.fired_at)).where(
        Alert.user_id == user_id,
        Alert.rule_id == rule.rule_id,
    )
    result = await db.execute(stmt)
    last_fired = result.scalar_one_or_none()

    if last_fired is None:
        return True  # chưa có alert nào → OK

    elapsed = (now - last_fired).total_seconds()
    return elapsed >= rule.cooldown_seconds


def _get_channel(rule: AlertRule) -> str:
    """Lấy channel từ action_json, mặc định 'toast'."""
    if rule.action_json and isinstance(rule.action_json, dict):
        if rule.action_json.get("toast"):
            return "toast"
        if rule.action_json.get("sound"):
            return "sound"
    return "toast"
```

---

### 7.7 `app/services/analytics_service.py`

**Flow — Daily Summary:**

```
Input: db, user_id, target_date (date)
    ↓
Query 1 — Focus/Break time:
    SELECT
        SUM( EXTRACT(EPOCH FROM (sb.end_at - sb.start_at)) )
            FILTER (WHERE sb.block_type = 'focus')    AS focus_seconds,
        SUM( EXTRACT(EPOCH FROM (sb.end_at - sb.start_at)) )
            FILTER (WHERE sb.block_type IN ('break','long_break'))  AS break_seconds,
        COUNT(DISTINCT ss.session_id) AS session_count
    FROM study_sessions ss
    JOIN session_blocks sb ON sb.session_id = ss.session_id
    WHERE ss.user_id = ?
      AND ss.started_at::date = target_date
    ↓
Query 2 — Distraction + Fatigue count:
    SELECT
        COUNT(*) FILTER (WHERE event_type LIKE 'DISTRACTION%'
                       OR event_type = 'FOCUS_OFFSCREEN'
                       OR event_type = 'ABSENT_AWAY')     AS distraction_count,
        COUNT(*) FILTER (WHERE event_type LIKE 'FATIGUE%') AS fatigue_count
    FROM ai_events
    WHERE user_id = ?
      AND start_at::date = target_date
    ↓
Combine → DailySummary
```

**Tại sao dùng raw SQL thay vì ORM?**

- Aggregate queries phức tạp (SUM, FILTER, EXTRACT) viết bằng ORM rất dài dòng.
- `text()` rõ ràng, dễ optimize, dễ debug.

**Code:**

```python
# app/services/analytics_service.py

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.analytics import DailySummary


async def get_daily_summary(
    db: AsyncSession, user_id: uuid.UUID, target_date: date
) -> DailySummary:
    # ── Query 1: Focus & Break time ──
    time_query = text("""
        SELECT
            COALESCE(SUM(
                EXTRACT(EPOCH FROM (sb.end_at - sb.start_at))
            ) FILTER (WHERE sb.block_type = 'focus'), 0)::int AS focus_seconds,

            COALESCE(SUM(
                EXTRACT(EPOCH FROM (sb.end_at - sb.start_at))
            ) FILTER (WHERE sb.block_type IN ('break', 'long_break')), 0)::int AS break_seconds,

            COUNT(DISTINCT ss.session_id)::int AS session_count
        FROM study_sessions ss
        JOIN session_blocks sb ON sb.session_id = ss.session_id
        WHERE ss.user_id = :user_id
          AND ss.started_at::date = :target_date
          AND sb.end_at IS NOT NULL
    """)

    time_result = await db.execute(
        time_query, {"user_id": str(user_id), "target_date": target_date.isoformat()}
    )
    time_row = time_result.mappings().one()

    # ── Query 2: Distraction & Fatigue counts ──
    event_query = text("""
        SELECT
            COALESCE(COUNT(*) FILTER (
                WHERE event_type IN ('DISTRACTION_PHONE', 'FOCUS_OFFSCREEN', 'ABSENT_AWAY')
            ), 0)::int AS distraction_count,

            COALESCE(COUNT(*) FILTER (
                WHERE event_type LIKE 'FATIGUE%%'
            ), 0)::int AS fatigue_count
        FROM ai_events
        WHERE user_id = :user_id
          AND start_at::date = :target_date
    """)

    event_result = await db.execute(
        event_query, {"user_id": str(user_id), "target_date": target_date.isoformat()}
    )
    event_row = event_result.mappings().one()

    return DailySummary(
        date=target_date,
        total_focus_seconds=time_row["focus_seconds"],
        total_break_seconds=time_row["break_seconds"],
        distraction_count=event_row["distraction_count"],
        fatigue_count=event_row["fatigue_count"],
        session_count=time_row["session_count"],
    )
```

### 7.8 `app/services/__init__.py`

```python
# app/services/__init__.py
# File rỗng
```

---

## 8. PHẦN F — Routers (API Endpoints)

### 8.1 Pattern chung

```python
# Mọi router đều:
#   1. Khai báo prefix và tags
#   2. Dùng Depends(get_current_user) → lấy user_id
#   3. Dùng Depends(get_db) → lấy AsyncSession
#   4. Gọi service function → không đặt logic ở đây
#   5. Return Pydantic Response schema

router = APIRouter(prefix="/api/v1/tasks", tags=["Tasks"])

@router.get("/", response_model=list[TaskResponse])
async def list_tasks(
    db: AsyncSession = Depends(get_db),           # DB session
    user_id: uuid.UUID = Depends(get_current_user), # Auth
    status: str | None = Query(None),              # Query params
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    return await task_service.list_tasks(db, user_id, status_filter=status, ...)
```

---

### 8.2 `app/routers/tasks.py`

```python
# app/routers/tasks.py

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse
from app.services import task_service

router = APIRouter(prefix="/api/v1/tasks", tags=["Tasks"])


@router.post("/", response_model=TaskResponse, status_code=201)
async def create_task(
    data: TaskCreate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    return await task_service.create_task(db, user_id, data)


@router.get("/", response_model=list[TaskResponse])
async def list_tasks(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
    status: str | None = Query(None, pattern=r"^(todo|doing|done|archived)$"),
    due_from: datetime | None = Query(None),
    due_to: datetime | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    return await task_service.list_tasks(
        db, user_id,
        status_filter=status, due_from=due_from, due_to=due_to,
        offset=offset, limit=limit,
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    return await task_service.get_task(db, user_id, task_id)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: uuid.UUID,
    data: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    return await task_service.update_task(db, user_id, task_id, data)


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    await task_service.delete_task(db, user_id, task_id)
```

---

### 8.3 `app/routers/sessions.py`

```python
# app/routers/sessions.py

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.study_session import SessionCreate, SessionEnd, SessionResponse
from app.services import session_service

router = APIRouter(prefix="/api/v1/sessions", tags=["Study Sessions"])


@router.post("/", response_model=SessionResponse, status_code=201)
async def create_session(
    data: SessionCreate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    return await session_service.create_session(db, user_id, data)


@router.get("/", response_model=list[SessionResponse])
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    return await session_service.list_sessions(
        db, user_id, date_from=date_from, date_to=date_to,
        offset=offset, limit=limit,
    )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    return await session_service.get_session(db, user_id, session_id)


@router.patch("/{session_id}/end", response_model=SessionResponse)
async def end_session(
    session_id: uuid.UUID,
    data: SessionEnd,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    return await session_service.end_session(db, user_id, session_id, data)
```

---

### 8.4 `app/routers/blocks.py`

```python
# app/routers/blocks.py

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.session_block import BlockCreate, BlockResponse
from app.services import block_service

router = APIRouter(prefix="/api/v1/blocks", tags=["Session Blocks"])


@router.post("/", response_model=BlockResponse, status_code=201)
async def create_block(
    data: BlockCreate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    return await block_service.create_block(db, user_id, data)


@router.get("/session/{session_id}", response_model=list[BlockResponse])
async def list_blocks(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    return await block_service.list_blocks_by_session(db, user_id, session_id)
```

---

### 8.5 `app/routers/ai_events.py`

```python
# app/routers/ai_events.py

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.ai_event import AiEventCreate, AiEventBatchCreate, AiEventResponse
from app.services import ai_event_service

router = APIRouter(prefix="/api/v1/ai-events", tags=["AI Events"])


@router.post("/", response_model=AiEventResponse, status_code=201)
async def create_event(
    data: AiEventCreate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    return await ai_event_service.create_event(db, user_id, data)


@router.post("/batch", response_model=list[AiEventResponse], status_code=201)
async def create_events_batch(
    data: AiEventBatchCreate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    return await ai_event_service.create_events_batch(db, user_id, data)


@router.get("/", response_model=list[AiEventResponse])
async def list_events(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
    event_type: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
):
    return await ai_event_service.list_events(
        db, user_id,
        event_type=event_type, date_from=date_from, date_to=date_to,
        offset=offset, limit=limit,
    )
```

---

### 8.6 `app/routers/alerts.py`

```python
# app/routers/alerts.py

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.alert_rule import AlertRuleCreate, AlertRuleUpdate, AlertRuleResponse
from app.schemas.alert import AlertResponse
from app.services import alert_service

router = APIRouter(prefix="/api/v1/alerts", tags=["Alerts"])


# ──── Alert Rules ────

@router.post("/rules", response_model=AlertRuleResponse, status_code=201)
async def create_rule(
    data: AlertRuleCreate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    return await alert_service.create_rule(db, user_id, data)


@router.get("/rules", response_model=list[AlertRuleResponse])
async def list_rules(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    return await alert_service.list_rules(db, user_id)


@router.get("/rules/{rule_id}", response_model=AlertRuleResponse)
async def get_rule(
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    return await alert_service.get_rule(db, user_id, rule_id)


@router.patch("/rules/{rule_id}", response_model=AlertRuleResponse)
async def update_rule(
    rule_id: uuid.UUID,
    data: AlertRuleUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    return await alert_service.update_rule(db, user_id, rule_id, data)


@router.delete("/rules/{rule_id}", status_code=204)
async def delete_rule(
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    await alert_service.delete_rule(db, user_id, rule_id)


# ──── Alert History ────

@router.get("/", response_model=list[AlertResponse])
async def list_alerts(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
    session_id: uuid.UUID | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
):
    return await alert_service.list_alerts(
        db, user_id, session_id=session_id, offset=offset, limit=limit,
    )
```

---

### 8.7 `app/routers/analytics.py`

```python
# app/routers/analytics.py

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.analytics import DailySummary
from app.services import analytics_service

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])


@router.get("/daily-summary", response_model=DailySummary)
async def daily_summary(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
    target_date: date = Query(..., description="Ngày cần xem, format: YYYY-MM-DD"),
):
    return await analytics_service.get_daily_summary(db, user_id, target_date)
```

### 8.8 `app/routers/__init__.py`

```python
# app/routers/__init__.py
# File rỗng
```

---

## 9. PHẦN G — Main Application (`main.py`)

### 9.1 Flow khởi động app

```
1. Import FastAPI
2. Import config, logging, exception handlers
3. Tạo FastAPI instance
4. Đăng ký CORS middleware
5. Đăng ký exception handlers
6. Đăng ký tất cả routers
7. Thêm health check endpoint
8. Startup/shutdown events (đóng engine)
```

### 9.2 Code

```python
# app/main.py

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging_config import setup_logging
from app.db.session import engine

# Import routers
from app.routers import tasks, sessions, blocks, ai_events, alerts, analytics


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup & shutdown events."""
    setup_logging()
    yield
    # Shutdown: đóng tất cả connections
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# ── CORS ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Exception Handlers ──
register_exception_handlers(app)

# ── Routers ──
app.include_router(tasks.router)
app.include_router(sessions.router)
app.include_router(blocks.router)
app.include_router(ai_events.router)
app.include_router(alerts.router)
app.include_router(analytics.router)


# ── Health Check ──
@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "version": settings.APP_VERSION}
```

---

## 10. PHẦN H — Chạy & Test

### 10.1 Setup ban đầu

```bash
# 1. Vào thư mục backend
cd backend

# 2. Activate venv (đã tạo sẵn)
source venv/bin/activate

# 3. Thư viện đã được cài sẵn. Nếu cần cài lại:
pip install -r requirements.txt

# 4. Copy .env
cp .env.example .env
# → Mở .env → điền:
#   DATABASE_URL=postgresql+asyncpg://postgres.[ref]:[pass]@....pooler.supabase.com:5432/postgres
#   SUPABASE_JWT_SECRET=<lấy từ Supabase Dashboard → Settings → API → JWT Secret>
```

### 10.2 Chạy server

```bash
# Development (auto-reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Mở browser: **http://localhost:8000/docs** → Swagger UI tự động.

### 10.3 Lấy JWT token để test

```bash
# Đăng nhập qua Supabase Auth API để lấy access_token
curl -X POST "https://YOUR_PROJECT.supabase.co/auth/v1/token?grant_type=password" \
  -H "apikey: YOUR_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "your-password"
  }'

# Response:
# { "access_token": "eyJhbGciOi...", "user": { "id": "uuid-..." } }

# Lưu token vào biến:
TOKEN="eyJhbGciOi..."
```

### 10.4 Example curl requests

```bash
# ── Health Check ──
curl http://localhost:8000/health

# ── Create Task ──
curl -X POST http://localhost:8000/api/v1/tasks/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Học Chapter 5 - Data Structures",
    "status": "todo",
    "priority": 3,
    "due_at": "2026-03-01T23:59:00Z",
    "estimated_minutes": 120,
    "subject_name": "Algorithms"
  }'

# ── List Tasks (filter by status) ──
curl "http://localhost:8000/api/v1/tasks/?status=todo&limit=10" \
  -H "Authorization: Bearer $TOKEN"

# ── Update Task ──
curl -X PATCH http://localhost:8000/api/v1/tasks/TASK_UUID_HERE \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "doing"}'

# ── Delete Task ──
curl -X DELETE http://localhost:8000/api/v1/tasks/TASK_UUID_HERE \
  -H "Authorization: Bearer $TOKEN"

# ── Create Study Session ──
curl -X POST http://localhost:8000/api/v1/sessions/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "planned_mode": "pomodoro",
    "started_at": "2026-02-28T08:00:00Z"
  }'

# ── End Session ──
curl -X PATCH http://localhost:8000/api/v1/sessions/SESSION_UUID/end \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "ended_at": "2026-02-28T09:30:00Z",
    "end_reason": "completed"
  }'

# ── Add Block ──
curl -X POST http://localhost:8000/api/v1/blocks/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "SESSION_UUID",
    "block_type": "focus",
    "start_at": "2026-02-28T08:00:00Z",
    "end_at": "2026-02-28T08:25:00Z"
  }'

# ── Insert AI Event (single) ──
curl -X POST http://localhost:8000/api/v1/ai-events/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "POSTURE_SLOUCH",
    "start_at": "2026-02-28T08:10:00Z",
    "end_at": "2026-02-28T08:10:08Z",
    "confidence": 0.87,
    "severity": 3,
    "payload_json": {"angle_deg": 32}
  }'

# ── Insert AI Events (batch) ──
curl -X POST http://localhost:8000/api/v1/ai-events/batch \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "events": [
      {
        "event_type": "FATIGUE_YAWN",
        "start_at": "2026-02-28T09:00:00Z",
        "end_at": "2026-02-28T09:00:03Z",
        "confidence": 0.92,
        "severity": 2
      },
      {
        "event_type": "DISTRACTION_PHONE",
        "start_at": "2026-02-28T09:05:00Z",
        "end_at": "2026-02-28T09:05:15Z",
        "confidence": 0.95,
        "severity": 5,
        "payload_json": {"phone_bbox": [100, 200, 300, 400]}
      }
    ]
  }'

# ── Create Alert Rule ──
curl -X POST http://localhost:8000/api/v1/alerts/rules \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Cảnh báo gù lưng",
    "trigger_event_type": "POSTURE_SLOUCH",
    "cooldown_seconds": 60,
    "condition_json": {"minConfidence": 0.6, "minDurationSec": 5},
    "action_json": {"toast": true, "sound": "beep"}
  }'

# ── List Alerts ──
curl "http://localhost:8000/api/v1/alerts/?limit=10" \
  -H "Authorization: Bearer $TOKEN"

# ── Daily Summary ──
curl "http://localhost:8000/api/v1/analytics/daily-summary?target_date=2026-02-28" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 📌 Thứ tự code khuyến nghị

| Bước   | File(s)                                                                                                                                             | Lý do                                          |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| **1**  | `app/__init__.py`, `core/__init__.py`, `db/__init__.py`, `models/__init__.py`, `schemas/__init__.py`, `services/__init__.py`, `routers/__init__.py` | Tạo package markers (file rỗng)                |
| **2**  | `app/core/config.py`                                                                                                                                | Mọi thứ đều cần config                         |
| **3**  | `app/core/logging_config.py`                                                                                                                        | Setup logging trước khi code tiếp              |
| **4**  | `app/db/session.py`                                                                                                                                 | Database layer — nền tảng                      |
| **5**  | `app/core/security.py`                                                                                                                              | Auth dependency — cần trước routers            |
| **6**  | `app/core/exceptions.py`                                                                                                                            | Error handling                                 |
| **7**  | `app/models/*.py`                                                                                                                                   | ORM models — map bảng Supabase                 |
| **8**  | `app/schemas/*.py`                                                                                                                                  | Pydantic schemas — request/response            |
| **9**  | `app/services/task_service.py`                                                                                                                      | Đơn giản nhất, code + test trước               |
| **10** | `app/routers/tasks.py`                                                                                                                              | Router đầu tiên, test end-to-end               |
| **11** | `app/main.py`                                                                                                                                       | Wire everything, chạy thử                      |
| **12** | Các services + routers còn lại                                                                                                                      | session → block → ai_event → alert → analytics |

---

## ⚠️ Lưu ý quan trọng

1. **KHÔNG** chạy `Base.metadata.create_all()` — bảng đã có trên Supabase.
2. **KHÔNG** dùng `service_role_key` cho API requests thông thường.
3. **KHÔNG** hardcode secret — luôn đọc từ `.env`.
4. **KHÔNG** đặt business logic trong router — chỉ gọi service.
5. **LUÔN** filter query bằng `user_id` từ JWT (double-layer với RLS).
6. Khi test, nhớ `.env` phải có đủ `DATABASE_URL` và `SUPABASE_JWT_SECRET`.
7. File `.env` **KHÔNG** được commit lên git (thêm vào `.gitignore`).

# 1️⃣ System Architecture Diagram

Tổng quan toàn bộ hệ thống: Frontend, Backend, Supabase, Camera AI và luồng dữ liệu.

```mermaid
flowchart TB
    subgraph CLIENT["🖥️ Client — Browser"]
        direction TB
        FE["Frontend\nReact / Next.js\n─────────────\nDashboard · Timer\nTask Manager · Analytics"]
        CAM["📷 Camera\ngetUserMedia API"]
        AI_LOCAL["🧠 AI Module (runs in browser)\nMediaPipe · TF.js\n─────────────\nPosture · Gaze · Phone · Fatigue"]
    end

    subgraph SUPABASE["☁️ Supabase"]
        direction TB
        AUTH["🔐 Auth\nJWT · OAuth\nRow Level Security"]
        API["⚡ PostgREST API\nAuto-generated REST\nfrom PostgreSQL"]
        DB["🗄️ PostgreSQL\nusers · user_settings\ntasks · study_sessions\nsession_blocks\nai_events · alert_rules · alerts"]
        RT["📡 Realtime\nWebSocket\nDB change subscriptions"]
        STORE["📦 Storage\nAvatars · CSV exports"]
        EDGE["⚙️ Edge Functions\nDeno runtime\nRule Engine · Webhooks"]
    end

    %% ─── Flows ───
    FE -- "① Auth (login/register)" --> AUTH
    FE -- "② CRUD tasks, sessions, settings" --> API
    API -- "read/write" --> DB
    DB -- "change events" --> RT
    RT -- "④ Push live updates" --> FE

    CAM -- "video frames (local)" --> AI_LOCAL
    AI_LOCAL -- "③ POST /ai_events (batch)" --> API

    API -- "trigger on INSERT ai_events" --> EDGE
    EDGE -- "evaluate alert_rules" --> DB
    EDGE -- "INSERT alerts" --> DB

    FE -- "upload avatar" --> STORE
    FE -- "export CSV" --> STORE

    style CLIENT  fill:#e3f2fd,stroke:#1976D2,stroke-width:2px
    style SUPABASE fill:#e8f5e9,stroke:#388E3C,stroke-width:2px
```

## Data Flow tóm tắt

| # | Actor | → | Destination | Nội dung |
|---|-------|---|-------------|----------|
| ① | User | → | Supabase Auth | Đăng nhập / đăng ký |
| ② | Frontend | → | PostgREST API | CRUD tasks, sessions |
| ③ | AI Module | → | PostgREST API | Ghi ai_events hàng loạt |
| ④ | Realtime | → | Frontend | Push cập nhật alerts/session live |
| ⑤ | Edge Function | → | PostgreSQL | Đánh giá luật → tạo alerts |

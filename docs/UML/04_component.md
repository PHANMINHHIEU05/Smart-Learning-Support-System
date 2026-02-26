# 4️⃣ Component Diagram — Backend Architecture

Phân rã nội bộ backend/edge functions theo layer để tránh spaghetti code.

```mermaid
flowchart TB
    subgraph FRONTEND["Frontend Layer"]
        FE_VIEW["View Components\nDashboard · Timer · Task Board\nAnalytics · Settings"]
        FE_HOOK["Custom Hooks\nuseSession · useAI\nuseAlert · useTasks"]
        FE_AI["AI Module\n─────────────────\nPoseDetector\nGazeTracker\nPhoneDetector\nFatigueDetector\nEventAggregator"]
        FE_WS["Realtime Client\nSupabase Realtime\nWebSocket listener"]
    end

    subgraph API_LAYER["API Layer (Supabase PostgREST)"]
        REST["Auto REST Endpoints\nGET/POST/PATCH/DELETE\n/users /tasks /study_sessions\n/session_blocks /ai_events\n/alert_rules /alerts"]
        AUTH_MW["Auth Middleware\nJWT Verification\nRow Level Security (RLS)"]
    end

    subgraph SERVICE_LAYER["Service Layer (Edge Functions — Deno)"]
        SESSION_SVC["SessionService\n─────────────\nstartSession()\nendSession()\ncreateBlock()\ngetSessionStats()"]
        ALERT_SVC["AlertService\n─────────────\nevaluateRules()\nfireAlert()\ncheckCooldown()\nbuildMessage()"]
        ANALYTICS_SVC["AnalyticsService\n─────────────\ngetDailySummary()\ngetWeeklyTrend()\ngetFocusScore()\ngetEventHeatmap()"]
    end

    subgraph RULE_ENGINE["Rule Engine"]
        RULE_EVAL["RuleEvaluator\n─────────────\nloadRules(user_id)\nmatchCondition(event, rule)\napplyAction(rule, event)"]
        CONDITION["ConditionChecker\n─────────────\ncheckMinDuration()\ncheckMinConfidence()\ncheckCooldown()"]
        ACTION["ActionDispatcher\n─────────────\ndispatchToast()\ndispatchSound()\npauseSession()"]
    end

    subgraph DB_LAYER["Database Layer (PostgreSQL via Supabase)"]
        TABLES["Tables\n─────────────\nusers · user_settings\ntasks\nstudy_sessions · session_blocks\nai_events\nalert_rules · alerts"]
        INDEXES["Indexes\n─────────────\n(user_id, started_at)\n(session_id, start_at)\n(event_type, start_at)\n..."]
        RLS["Row Level Security\n─────────────\nauth.uid() = user_id\n(mọi bảng)"]
        TRIGGERS["DB Triggers\n─────────────\nON ai_events INSERT\n→ invoke edge function"]
    end

    subgraph AI_MODULE["AI Module (Browser-side)"]
        MP["MediaPipe\nFace Landmarker\nPose Landmarker"]
        DETECTORS["Detectors\n─────────────\nPostureAnalyzer\nGazeTracker\nPhoneDetector\nFatigueDetector"]
        AGGREGATOR["EventAggregator\n─────────────\ndebounce(5s)\nbatch events\nPOST to API"]
    end

    %% ─── Connections ───
    FE_VIEW --> FE_HOOK
    FE_HOOK --> REST
    FE_HOOK --> FE_AI
    FE_WS   --> FE_HOOK
    FE_AI   --> AI_MODULE

    REST --> AUTH_MW
    AUTH_MW --> TABLES

    REST --> SESSION_SVC
    REST --> ANALYTICS_SVC

    TRIGGERS --> ALERT_SVC
    ALERT_SVC --> RULE_ENGINE
    RULE_EVAL --> CONDITION
    RULE_EVAL --> ACTION
    ACTION --> TABLES

    SESSION_SVC --> TABLES
    ANALYTICS_SVC --> TABLES
    ANALYTICS_SVC --> INDEXES

    TABLES --> RLS
    TABLES --> TRIGGERS

    MP --> DETECTORS
    DETECTORS --> AGGREGATOR
    AGGREGATOR --> REST

    style FRONTEND      fill:#e3f2fd,stroke:#1976D2,stroke-width:1px
    style API_LAYER     fill:#f3e5f5,stroke:#7B1FA2,stroke-width:1px
    style SERVICE_LAYER fill:#fff3e0,stroke:#E65100,stroke-width:1px
    style RULE_ENGINE   fill:#fce4ec,stroke:#C62828,stroke-width:1px
    style DB_LAYER      fill:#e8f5e9,stroke:#2E7D32,stroke-width:1px
    style AI_MODULE     fill:#e0f7fa,stroke:#00695C,stroke-width:1px
```

## Mô tả từng layer

| Layer | Trách nhiệm | Công nghệ |
|-------|-------------|-----------|
| **View Components** | UI render, user interaction | React / Next.js |
| **Custom Hooks** | State management, side effects | React Hooks + Supabase SDK |
| **AI Module** | Phân tích hình ảnh camera real-time | MediaPipe, TF.js |
| **EventAggregator** | Debounce + batch POST ai_events (tránh spam) | JavaScript |
| **API Layer** | REST endpoints, auth enforcement | Supabase PostgREST + RLS |
| **SessionService** | Lifecycle phiên học, tính toán blocks | Edge Function (Deno) |
| **AlertService** | Nhận event → gọi Rule Engine → tạo alert | Edge Function (Deno) |
| **AnalyticsService** | Tổng hợp số liệu theo ngày/tuần | Edge Function (Deno) |
| **Rule Engine** | Đánh giá điều kiện, cooldown, dispatch action | Edge Function (Deno) |
| **DB Layer** | PostgreSQL với RLS, indexes, triggers | Supabase PostgreSQL |

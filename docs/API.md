# AI Car Mechanic Assistant — REST API Reference

Base URL: `<BACKEND_URL>`

All endpoints return JSON responses. Errors follow standard structure:
```json
{
  "error": {
    "code": "error_code",
    "message": "Human readable explanation",
    "details": {}
  }
}
```

---

## 1. System & Health

### `GET /api/health/`
Returns database connectivity and operational status.

**Response `200 OK`**:
```json
{
  "status": "ok",
  "db": true
}
```

---

### `GET /api/stats/`
Returns system usage metrics, conversation counts, and AI telemetry.

**Response `200 OK`**:
```json
{
  "conversations": 42,
  "messages_total": 184,
  "bot_messages_total": 92,
  "diagnoses": 38,
  "bookings": 19,
  "ai_calls_total": 12,
  "ai_cache_hits": 5,
  "ai_failures": 0,
  "ai_call_ratio": 0.1304,
  "by_purpose": {
    "media_image": 4,
    "media_audio": 2,
    "media_video": 1,
    "extract_text": 5
  }
}
```

---

## 2. Interactive Chat

### `POST /api/chat/`
Submits a conversational turn, choice selection, or uploaded media attachments.

**Request Body**:
```json
{
  "conversation_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "client_msg_id": "cm-9a81b2c",
  "text": "My front brakes squeal loudly whenever I slow down",
  "choice": {
    "question_id": "q_brake_when",
    "option_id": "only_braking",
    "label": "Only when braking"
  },
  "upload_ids": ["7d2b45a0-9c2b-4e12-b911-3c5889e47192"]
}
```

**Response `200 OK`**:
```json
{
  "conversation_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "messages": [
    {
      "id": "msg-123",
      "sender": "bot",
      "text": "When do you hear the brake noise?",
      "kind": "question",
      "meta": {
        "suggested_replies": [
          { "id": "only_braking", "label": "Only when braking", "question_id": "q_brake_when" },
          { "id": "all_the_time", "label": "Constantly while rolling", "question_id": "q_brake_when" },
          { "id": "unknown", "label": "Not sure", "question_id": "q_brake_when" }
        ]
      }
    }
  ],
  "suggested_replies": [
    { "id": "only_braking", "label": "Only when braking", "question_id": "q_brake_when" }
  ],
  "diagnosis": null,
  "actions": null
}
```

---

## 3. Conversations

### `GET /api/conversations/`
Retrieves conversations filtered by IDs.
- Query Parameter: `ids=uuid1,uuid2`

### `GET /api/conversations/{id}/`
Returns conversation details with full message history.

---

## 4. Diagnostic Assessment

### `POST /api/diagnosis/`
Forces calculation of current diagnosis from existing conversation history.

**Request Body**:
```json
{
  "conversation_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "force": true
}
```

### `GET /api/diagnosis/{id}/`
Retrieves stored diagnosis record, ranking breakdown, and recommended repair package.

---

## 5. Media Uploads

### `POST /api/uploads/`
Multipart file upload (`file`). Accepts images (JPEG, PNG, WebP up to 5MB), audio (MP3, WAV, WebM up to 10MB), and video (MP4, QuickTime up to 25MB).

**Response `201 Created`**:
```json
{
  "id": "7d2b45a0-9c2b-4e12-b911-3c5889e47192",
  "original_name": "rotor_wear.jpg",
  "mime_type": "image/jpeg",
  "size_bytes": 1420580,
  "kind": "image",
  "file_url": "/media/uploads/2026/09/24/rotor_wear.jpg",
  "analysis_status": "pending",
  "analysis_result": {},
  "created_at": "2026-09-24T12:00:00Z"
}
```

### `GET /api/uploads/{id}/`
Returns upload status and cached AI inspection observations.

---

## 6. Mechanic Booking

### `POST /api/booking/`
Schedules an in-person diagnostic and repair visit. Supports `Idempotency-Key` header.

**Request Headers**:
- `Idempotency-Key`: `bk-9f8a2bc7190`

**Request Body**:
```json
{
  "customer_name": "Rajesh Sharma",
  "phone": "9812345670",
  "city": "Meerut",
  "scheduled_at": "2026-09-25T10:00:00Z",
  "service_key": "brake_service",
  "conversation_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
}
```

**Response `201 Created`**:
```json
{
  "id": "5b4c12d8-912f-410a-81f0-7bfa0092182a",
  "customer_name": "Rajesh Sharma",
  "phone": "9812345670",
  "city": "Meerut",
  "service": {
    "key": "brake_service",
    "name": "Brake pad & disc service",
    "price_min": 1500,
    "price_max": 6000,
    "duration_hours": 2.0,
    "currency": "INR"
  },
  "mechanic": {
    "id": 1,
    "name": "Rajesh Kumar",
    "city": "Meerut",
    "phone": "+91 98123 45670"
  },
  "scheduled_at": "2026-09-25T10:00:00Z",
  "status": "confirmed",
  "created_at": "2026-09-24T12:30:00Z"
}
```

**Response `409 Conflict` (All mechanics booked)**:
```json
{
  "error": {
    "code": "slot_unavailable",
    "message": "No mechanic is available at the requested time slot.",
    "details": {
      "alternatives": [
        "2026-09-25T11:00:00Z",
        "2026-09-25T14:00:00Z",
        "2026-09-26T10:00:00Z"
      ]
    }
  }
}
```

### `GET /api/booking/{id}/`
Retrieves receipt and status for a confirmed mechanic booking.

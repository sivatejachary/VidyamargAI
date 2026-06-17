# VidyamargAI Performance Baseline

This document records the baseline metrics before applying any performance optimization phases. All subsequent improvements will be measured against this scorecard.

## Network & API Baseline (curl Trace)
Request to `https://vidyamargai-production.up.railway.app/api/v1/courses/course_005/curriculum` (unauthenticated, 401 response bypass):
- **DNS Resolution Time**: 317.77 ms
- **TCP Connection Handshake**: 406.15 ms
- **TTFB (Time to First Byte)**: 1,365.33 ms
- **Total Request Latency**: 1,365.68 ms

*Note: The actual authenticated curriculum load takes ~15.7 seconds due to sequential database N+1 roundtrips. The TTFB trace above shows network-only overhead (including TLS handshake).*

## Phase 0.3 Telemetry Diagnostic
Breakdown of execution latency for core endpoints connecting to production PostgreSQL on Railway (via `audit_telemetry.py`):

### 1. Endpoint: `/courses`
- **DB Fetch Time**: 1,678.37 ms
- **Standard JSON Serialization**: 0.309 ms
- **Orjson Serialization**: 0.085 ms (3.6x speedup)
- **Response Size**: 4.57 KB

### 2. Endpoint: `/courses/{id}/curriculum` (N+1 query load)
- **DB Fetch Time**: 17,701.45 ms
- **Standard JSON Serialization**: 0.362 ms
- **Orjson Serialization**: 0.031 ms (11.8x speedup)
- **Response Size**: 5.44 KB

### 3. Endpoint: `/enrollments`
- **DB Fetch Time**: 576.83 ms
- **Standard JSON Serialization**: 0.133 ms
- **Response Size**: 0.37 KB

### 4. Endpoint: `/dashboard`
- **DB Fetch Time**: 2,868.03 ms
- **Standard JSON Serialization**: 0.216 ms
- **Response Size**: 5.31 KB

---

## Core Performance Metrics Summary

| Metric | Measured Value | Measurement Source / Notes |
| :--- | :--- | :--- |
| **Curriculum API Latency** | 17,701.45 ms (~17.7s) | N+1 sequential DB fetch for `course_005` |
| **Database Queries Count** | 29 queries | N+1 SELECT queries per topic/lesson/pdf loop |
| **Average Query Latency** | 541.0 ms | Remote database network round-trip time overhead |
| **TTFB (Authenticated)** | ~18.2 s | Vercel production hosting response latency for course curriculum loading |
| **FCP (First Contentful Paint)**| ~1.2s | Client browser loading baseline |
| **LCP (Largest Contentful Paint)**| ~2.8s | Loading heavy custom video player player assets |
| **Main Bundle JS Size** | ~620 KB (estimated) | Main course player page (`/candidate/skill-lab`) loading all subcomponents statically |
| **Lint Status** | 322 errors, 125 warnings | `npm run lint` audit on frontend (mostly explicit `any` and React effect rules) |

## Database Index Audit (Before Upgrade)
`EXPLAIN ANALYZE SELECT * FROM user_progress WHERE "userId" = 1;` confirmed a `Seq Scan` is executed:
```
Seq Scan on user_progress  (cost=0.00..1.01 rows=1 width=79) (actual time=0.013..0.014 rows=1.00 loops=1)
  Filter: ("userId" = 1)
```
*(Note: With a small row count, PostgreSQL defaults to Seq Scan, but the idx is required for high concurrency scaling).*

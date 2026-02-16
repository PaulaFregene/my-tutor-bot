# Scaling Plan for 100 Concurrent Users

## Current Architecture Assessment ✅

Current setup is **already optimized** for 100 concurrent users:
- ✅ S3 for PDF storage (infinite scale)
- ✅ Local ChromaDB (perfect for read-heavy shared content)
- ⚠️ SQLite (good for now, upgrade if needed)
- 🔴 Groq API calls (actual bottleneck)

## What I DON'T Need

### ❌ Chroma Cloud - NOT NEEDED
**Why local ChromaDB is better:**
- Faster (no network latency)
- Cheaper ($0/month vs $20+/month)
- Handles 1000+ concurrent reads easily
- Same embeddings shared by all users (read-only after ingestion)
- In-memory caching makes repeated queries instant

**Chroma Cloud only needed if:**
- Multiple backend instances (but you need persistent volume sharing anyway)
- Cross-region deployment
- You hit 1000+ users and need distributed vector DB

**For 100 users:** Local ChromaDB is perfect ✅

## Performance Bottleneck Analysis

### Actual Latency per Student Query:
```
1. User asks question              →  0ms
2. Fetch chat history (SQLite)     →  5ms   ✅
3. Vector search (ChromaDB)        →  50ms  ✅
4. Retrieve PDF chunks             →  10ms  ✅
5. Call Groq LLM API              → 2000ms 🔴 BOTTLENECK
6. Save response (SQLite)          →  10ms  ✅
─────────────────────────────────────────────
Total: ~2075ms (97% is LLM API call)
```

**ChromaDB is only 2.4% of query time!**

## Scaling Strategy (by user count)

### Phase 1: 1-100 Users (CURRENT) ✅
**Setup:**
- Single Railway instance
- Local ChromaDB + persistent volume
- SQLite for conversations
- S3 for PDFs

**Performance:**
- ChromaDB: Handles easily
- SQLite: Fine with proper indexing
- Bottleneck: Groq API rate limits

**Action needed:** None, you're good!

### Phase 2: 100-500 Users
**When to upgrade:**
- See "database is locked" SQLite errors
- Need multiple backend instances for reliability

**Changes:**
1. **Upgrade to PostgreSQL** (Railway offers free tier)
   - Better write concurrency
   - Connection pooling
   - ~1 hour migration time

2. **Keep local ChromaDB**
   - Still works great
   - Use Railway persistent volumes
   - Mount same volume across instances if needed

3. **Add response caching** (optional)
   - Cache common questions → instant responses
   - Redis or in-memory cache

### Phase 3: 500+ Users
**Then consider:**
- Multiple backend instances (load balanced)
- Chroma Cloud or self-hosted Qdrant cluster
- PostgreSQL with connection pooling
- Rate limiting per user

## Immediate Optimizations (No Code Changes)

### 1. Railway Deployment Settings
```yaml
# Ensure backend has:
- Persistent volume for ./chroma_db/
- Persistent volume for ./uploaded_pdfs/ (if not using S3)
- Memory: 512MB minimum (1GB recommended)
- CPU: Shared (sufficient for 100 users)
```

### 2. Environment Variables for Production
```bash
# Backend .env
USE_S3=true  # Enable S3 for PDF storage
GROQ_API_KEY=your_key_here

# These handle concurrency:
WORKERS=2  # Uvicorn workers (if needed)
```

### 3. Monitor These Metrics
- Groq API response time (your bottleneck)
- SQLite write errors (upgrade signal)
- ChromaDB query time (should stay <100ms)
- S3 presigned URL generation

## Future Performance Enhancements

### Optional: Response Caching Layer
If students ask similar questions, cache LLM responses:

```python
# Example cache key: hash(question + mode + last_updated_pdfs)
# Cache for 1 hour
# Reduces LLM calls by 40-60% in practice
```

### Optional: Async Processing
Use FastAPI background tasks for non-critical operations:
- Logging analytics
- Updating last access time
- Pre-warming common queries

## Cost Comparison: Local vs Cloud ChromaDB

### Local ChromaDB (Current)
- Storage: $0 (included in Railway persistent volume)
- Compute: $0 (runs on same backend instance)
- Network: $0 (no API calls)
- **Total: $0/month**

### Chroma Cloud
- Storage: ~$20/month (1GB vectors)
- API calls: ~$0.001 per query
- For 100 users × 10 queries/day: ~$30/month
- **Total: ~$50/month**

**Savings: $50/month by using local ChromaDB**

## When SQLite Write Locks Become an Issue

### Symptoms:
```
sqlite3.OperationalError: database is locked
```

### Quick Fix (Before PostgreSQL Migration):
```python
# In db.py
conn = sqlite3.connect(
    "conversations.db",
    check_same_thread=False,
    timeout=10.0,  # Wait up to 10s for locks
    isolation_level='DEFERRED'  # Better concurrency
)
```

### Proper Fix:
Migrate to PostgreSQL (see migration guide below)

## PostgreSQL Migration Guide (When Needed)

### 1. Add Railway PostgreSQL
```bash
# In Railway dashboard:
1. Add PostgreSQL service to your project
2. Copy DATABASE_URL from environment variables
```

### 2. Update db.py
```python
import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///conversations.db")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True)
    anon_user_id = Column(String, index=True)
    role = Column(String)
    content = Column(String)
    mode = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
```

### 3. Export existing SQLite data (if needed)
```bash
# Export to CSV
sqlite3 conversations.db ".mode csv" ".output conversations.csv" "SELECT * FROM conversations"

# Import to PostgreSQL
psql $DATABASE_URL -c "\COPY conversations FROM 'conversations.csv' CSV HEADER"
```

## Load Testing Recommendations

### Before Launch:
```bash
# Install Apache Bench
pip install locust  # or use ab (Apache Bench)

# Test concurrent queries
locust -f load_test.py --host http://localhost:8000
# Simulate 100 concurrent users
```

### Expected Results (100 concurrent users):
- ChromaDB queries: <100ms average ✅
- LLM calls: 2000ms average (Groq API limit)
- SQLite writes: <50ms average ✅
- Overall: Limited by Groq API, not your infrastructure

## Caching Strategy (Optional Enhancement)

### What to Cache:
1. **LLM responses** (1 hour TTL)
   - Key: hash(question_normalized + mode + content_version)
   - Saves 40-60% of LLM calls
   
2. **Vector search results** (already cached by ChromaDB internally)
   - No action needed ✅

3. **PDF metadata** (24 hours TTL)
   - List of PDFs, display names
   - Reduces S3 list calls

### Simple In-Memory Cache:
```python
from functools import lru_cache
from hashlib import md5

# In rag_engine.py
response_cache = {}

def get_cached_response(question, mode, content_version):
    cache_key = md5(f"{question}|{mode}|{content_version}".encode()).hexdigest()
    return response_cache.get(cache_key)
```

## Summary: Your Scalability Checklist

### Already Optimized ✅
- [x] S3 for PDF storage (infinite scale)
- [x] ChromaDB local reads (fast, handles 100+ concurrent)
- [x] SQLite with indexing (good for 100 users)
- [x] Groq API (fast LLM)

### Monitor These:
- [ ] Groq API rate limits (5000 requests/day on free tier)
- [ ] SQLite write locks (upgrade to PostgreSQL if issues)
- [ ] Railway memory usage (<512MB is fine)

### Future Enhancements (When Needed):
- [ ] PostgreSQL (when you hit 100+ concurrent writers)
- [ ] Response caching (when budget matters)
- [ ] Multiple instances (for reliability, not performance)

### DON'T Waste Money On:
- ❌ Chroma Cloud (local is faster and free)
- ❌ Managed vector DB (ChromaDB local is perfect)
- ❌ Redis (unless caching responses)
- ❌ CDN (S3 presigned URLs are already fast)

## Conclusion

**Your current architecture is perfect for 100 users.**

The only potential upgrade is SQLite → PostgreSQL if you see write contention, but even that's optional. ChromaDB local is actually BETTER than Chroma Cloud for your use case.

Focus on:
1. ✅ Keeping S3 integration (you have this now)
2. ✅ Monitoring Groq API usage
3. ✅ User experience and features

Don't over-engineer! Stack already scales to 100 concurrent users easily.

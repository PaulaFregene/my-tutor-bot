# Railway Deployment Guide for MyTutorBot

## Setup Steps

### 1. Create a Railway Account
- Go to https://railway.app
- Sign up with GitHub
- Create a new project

### 2. Setup AWS S3 for PDF Storage (Recommended for Production)

#### Create S3 Bucket
#### Create IAM User for S3 Access

#### S3 Bucket Settings Explained

**Default Encryption (SSE-S3):**
- ✅ Keep the default - PDFs are automatically encrypted at rest
- AWS manages the encryption keys
- No additional cost
- Transparent to application

**Object Lock:**
- ❌ Keep DISABLED -  need to allow PDF deletion
- Object lock prevents deletion (used for compliance/legal holds)
- Would break admin's ability to delete/update course materials
- Only enable if  have regulatory requirements (WORM compliance)

**Versioning:**
- ✅ Recommended - allows PDF recovery if accidentally deleted
- Minimal cost (only stores changes)
- Can be disabled if you don't need it

**Block Public Access:**
- ✅ Keep ALL settings ON - security best practice
- Your app uses presigned URLs (temporary, secure links)
- PDFs remain private, only accessible via your backend

### 3. Deploy Backend Service
```bash
# In the Railway dashboard:
# 1. New Service → GitHub Repo
# 2. Select your my-tutor-bot repository
# 3. Set up the following environment variables:

# Required
GROQ_API_KEY=<your_groq_api_key>

# S3 Configuration (for production)
USE_S3=true
AWS_ACCESS_KEY_ID=<your_aws_key_from_step_2>
AWS_SECRET_ACCESS_KEY=<your_aws_secret_from_step_2>
AWS_S3_BUCKET=my-tutor-bot-pdfs
AWS_REGION=us-east-1

# Optional - only if using these services
# LLAMA_CLOUD_API_KEY=<your_llama_cloud_key>
# CHROMA_API_KEY=<your_chroma_cloud_key>
```

### 4. Deploy Frontend Service
```bash
# Add another service using the same repository
# Set the following environment variables:

NEXT_PUBLIC_API_URL=<backend_railway_url>
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=<your_clerk_key>
CLERK_SECRET_KEY=<your_clerk_secret>
```

### 5. Configure Backend Service Settings
- Go to Settings → Deploy
- Set the following start command:
  ```
  uvicorn main:app --host 0.0.0.0 --port $PORT
  ```
- Root directory: `backend/`

### 6. Configure Frontend Service Settings
- Go to Settings → Deploy
- Root directory: `frontend/`
- Build command: `npm run build`
- Start command: `npm start`

### 7. Link Frontend to Backend
- Get your backend service URL from Railway
- Update NEXT_PUBLIC_API_URL in frontend environment variables
- Redeploy frontend

## S3 Storage Mode

### How it Works

**When USE_S3=true (Production):**
- PDFs uploaded via `/api/upload` are saved to both local cache and S3
- List files reads from S3
- RAG ingestion downloads PDFs from S3 if not in local cache
- Delete operations remove from both S3 and local cache
- Frontend gets presigned URLs for direct PDF access

**When USE_S3=false (Local Development):**
- All PDFs stored in `./uploaded_pdfs/` directory
- No S3 API calls made
- Perfect for development and testing

### S3 Cost Estimation
- Storage: ~$0.023 per GB/month
- Requests: ~$0.0004 per 1000 GET requests
- For typical tutoring app: < $1/month

## Optional: Chroma Cloud (Not Currently Used)

## Optional: Chroma Cloud (Not Currently Used)
1. Go to https://cloud.trychroma.com
2. Create an account and get your API key
3. Add the key to your backend environment variables
4. Note: Currently using local ChromaDB (no need to set up unless migrating)

## Local Development

```bash
# 1. Copy environment template
cd backend
cp .env.example .env

# 2. Edit .env and add your GROQ_API_KEY
# Set USE_S3=false (or leave commented out)

# 3. Run with Docker Compose
cd ..
docker-compose up

# Or run manually:
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload

cd ../frontend
npm install
npm run dev
```

## Important Notes

### Performance & Scalability
- **For 100 concurrent users:** Current setup is perfect, no Chroma Cloud needed!
- **See [SCALING_PLAN.md](SCALING_PLAN.md)** for detailed scalability analysis
- Local ChromaDB is faster and cheaper than Chroma Cloud for shared content
- SQLite with WAL mode handles 100+ concurrent readers easily
- Bottleneck is LLM API calls (Groq), not your infrastructure

### Environment Variables
- Railway auto-detects Node.js and Python apps
- Use environment variables, NOT hardcoded values
- Keep `.env` and `.env.local` files in `.gitignore`
- Test locally first before deploying

### S3 Configuration
- **Development**: Set `USE_S3=false` or leave unset
- **Production**: Set `USE_S3=true` and configure AWS credentials
- S3 is optional but recommended for production scalability
- Local storage works fine for development and small deployments

### Database
- Currently using SQLite for conversation history (works for single instance)
- Consider Railway PostgreSQL if you need multiple backend instances
- ChromaDB uses local persistence (in ./chroma_db/)

### File Storage Strategy
- **Local mode**: Files in `./uploaded_pdfs/`, backed up in Railway volumes
- **S3 mode**: Files in S3, local directory acts as cache
- RAG ingestion always needs local access (downloads from S3 if needed)

## Troubleshooting

### General Issues
- Check Railway logs in the dashboard
- Ensure all environment variables are set correctly
- Verify CORS is configured for your domain

### S3-Specific Issues

**PDFs not uploading:**
- Check AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are correct
- Verify S3 bucket name matches AWS_S3_BUCKET
- Check IAM user has PutObject permission
- Look for S3 errors in Railway logs

**PDFs not appearing in chat:**
- Run `/api/ingest` after uploading PDFs
- Check if PDFs downloaded from S3 successfully (look for "[INGEST]" logs)
- Verify ChromaDB is persisting (check Railway volumes)

**403 Forbidden errors:**
- IAM policy may be incorrect
- Bucket name might be wrong
- Check bucket region matches AWS_REGION

**Cost concerns:**
- Monitor AWS billing dashboard
- Set up billing alerts
- Consider S3 Lifecycle policies to archive old PDFs

### Switching Between Local and S3 Storage
```bash
# To switch from local to S3:
1. Set USE_S3=true in environment variables
2. Upload existing PDFs to S3 bucket manually or re-upload via admin panel
3. Run /api/ingest to reindex

# To switch from S3 to local:
1. Set USE_S3=false
2. Download PDFs from S3 to ./uploaded_pdfs/
3. Run /api/ingest to reindex
```

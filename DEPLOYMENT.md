# Railway Deployment Guide for MyTutorBot

## Overview

This is a monorepo with two services:
- **Backend**: FastAPI service running on port 8000
- **Frontend**: Next.js service running on port 3000

Both services will be deployed as separate Railway services within a single Railway project.

## Setup Steps

### 1. Create a Railway Account
- Go to https://railway.app
- Sign up with GitHub
- Create a new project

### 2. Deploy Backend Service to Railway

#### Step 1: Add Backend Service
1. In your Railway project, click **+ New**
2. Select **GitHub Repo**
3. Connect to your `my-tutor-bot` repository
4. In the deployment settings:
   - **Root Directory**: `backend/`
   - **Dockerfile**: Use the default (it will detect `backend/Dockerfile`)
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

#### Step 2: Set Backend Environment Variables
Add these environment variables in Railway's environment tab:

```
# Required
GROQ_API_KEY=<your_groq_api_key>
FRONTEND_URL=https://<your-frontend-railway-url>

# S3 Configuration (recommended for production)
USE_S3=true
AWS_ACCESS_KEY_ID=<your_aws_key>
AWS_SECRET_ACCESS_KEY=<your_aws_secret>
AWS_S3_BUCKET=my-tutor-bot-pdfs
AWS_REGION=us-east-1

# Optional
# LLAMA_CLOUD_API_KEY=<your_llama_cloud_key>
# CHROMA_API_KEY=<your_chroma_cloud_key>
```

#### Step 3: Deploy Backend
- Railway will automatically build and deploy
- Copy the **Backend Service URL** (you'll need this for frontend)

### 3. Setup AWS S3 for PDF Storage (Recommended for Production)

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

### 4. Deploy Frontend Service to Railway

#### Step 1: Add Frontend Service
1. In your Railway project, click **+ New**
2. Select **GitHub Repo**
3. Connect to your `my-tutor-bot` repository again (same repo as backend)
4. In the deployment settings:
   - **Root Directory**: `frontend/`
   - **Dockerfile**: Use the default (it will detect `frontend/Dockerfile`)
   - **Build Command**: `npm run build`
   - **Start Command**: `next start -p $PORT`

#### Step 2: Set Frontend Environment Variables
Add these environment variables (get your backend URL from step 2.3):

```
NEXT_PUBLIC_API_URL=https://<your-backend-railway-url>
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=<your_clerk_publishable_key>
CLERK_SECRET_KEY=<your_clerk_secret_key>
```

#### Step 3: Deploy Frontend
- Railway will automatically build and deploy
- Get your frontend URL from Railway

### 5. Link Services Together
1. Update **FRONTEND_URL** in your backend environment variables:
   ```
   FRONTEND_URL=https://<your-frontend-railway-url>
   ```
2. The services are now communicating with each other

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

## Railway Monorepo Deployment Options

### Option 1: Using railway.json (Recommended)
A `railway.json` file at the root of your repo automatically configures both services. This file is already created in your repo and specifies:
- Backend service with proper Dockerfile and startup command
- Frontend service with proper Dockerfile and startup command
- Custom environment variables for each service

Simply push to GitHub and Railway will automatically:
1. Detect the railway.json configuration
2. Create/update both backend and frontend services
3. Use the specified Dockerfiles from each directory

### Option 2: Manual Configuration in Railway Dashboard
If you prefer not to use railway.json:
1. Create backend service manually (see section 2)
2. Create frontend service manually (see section 4)
3. Configure environment variables for each

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
- Check Railway logs in the dashboard (select each service separately)
- Ensure all environment variables are set correctly
- Verify CORS is configured for your domain
- Ensure backend URL in frontend's NEXT_PUBLIC_API_URL is correct

### Service Communication Issues

**Frontend can't reach backend:**
1. Check that `NEXT_PUBLIC_API_URL` in frontend has the correct backend Railway URL
2. Ensure backend includes your frontend URL in `FRONTEND_URL` environment variable
3. Check backend logs for CORS errors
4. Verify backend health endpoint: `GET <backend-url>/health`

**Backend health check failing:**
1. Check Railway deployment logs for errors during startup
2. Verify all environment variables are set (especially GROQ_API_KEY)
3. Check that Python dependencies installed correctly
4. Look for LlamaIndex initialization errors in logs

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

## Managing Two Services in Railway

### Viewing Logs
- Each service has its own logs in Railway dashboard
- Click on "Backend" service ? click "Logs" tab to see backend logs
- Click on "Frontend" service ? click "Logs" tab to see frontend logs
- Use the timestamp and search filters to debug specific issues

### Redeploying Individual Services
- Each service redeploys automatically when you push changes to its directory
- Push changes to /backend ? only backend service rebuilds
- Push changes to /frontend ? only frontend service rebuilds
- Push changes to root files ? no services rebuild unless referenced in Dockerfiles

### Monitoring Resource Usage
- Go to Railway project dashboard
- Each service card shows CPU, memory, and network usage in real-time
- Click service ? Metrics tab for detailed usage graphs
- Scale vertically by upgrading service plan if needed

### Environment Variable Management

**For Backend Service:**
1. Click on "Backend" service in Railway dashboard
2. Go to "Variables" tab
3. Add/edit environment variables:
   - `GROQ_API_KEY` - required for LLM
   - `FRONTEND_URL` - for CORS, set this after frontend deployment
   - S3 credentials if using `USE_S3=true`

**For Frontend Service:**
1. Click on "Frontend" service in Railway dashboard
2. Go to "Variables" tab
3. Add/edit environment variables:
   - `NEXT_PUBLIC_API_URL` - backend Railway service URL
   - `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` - from Clerk dashboard
   - `CLERK_SECRET_KEY` - from Clerk dashboard

**Recommended Variable Update Workflow:**
1. Deploy backend first, allow it to fully build and start
2. Copy backend service URL from Railway
3. Paste into frontend's `NEXT_PUBLIC_API_URL` environment variable
4. Frontend automatically redeploys with correct backend URL
5. Copy frontend service URL from Railway
6. Update backend's `FRONTEND_URL` environment variable
7. Backend automatically redeploys with correct frontend URL

### Database and Persistent Storage

**Backend Volumes:**
- Railway automatically creates volumes for:
  - `/app/chroma_db/` - ChromaDB vector database (survives restarts)
  - `/app/uploaded_pdfs/` - PDF cache directory (survives restarts)
- Data persists even if container restarts
- To reset data: Delete the volume in Railway's Data tab (irreversible)

**Frontend (Stateless):**
- No persistent storage needed
- Static files rebuilt on each deployment
- Safe to restart anytime without data loss

### Cost Monitoring
- Railway shows pricing in the project dashboard
- Each service is billed separately (Backend + Frontend)
- Free tier includes 500 hours/month per service (more than enough)
- Premium: /month per service for 24/7 uptime with autoscaling
- View detailed billing at: https://railway.app/account/billing

### Debugging Deployment Failures

**When a service fails to deploy:**
1. Check the Deployment Logs in Railway (not git commit logs)
2. Click the failed service ? Deployments tab ? click the failed deployment
3. Read through build logs for error messages

**Common issues and solutions:**
- "Port already in use" ? Ensure `` environment variable is set and used in start command
- "requirements.txt not found" ? Verify `backend/requirements.txt` file exists and is committed to git
- "package.json not found" ? Verify `frontend/package.json` file exists and is committed to git
- "Module not found" errors ? Check `backend/requirements.txt` has all dependencies
- Build hangs during pip install ? Normal for PyTorch/ChromaDB (takes 5-10 min), don't restart prematurely
- Health check failing ? Backend takes time to initialize LLM models, check logs for initialization progress

### Accessing Railway Services

**Get your service URLs:**
1. Go to Railway dashboard
2. Click on Backend service ? "Public Networking" tab ? copy Railway domain (ends in railway.app)
3. Click on Frontend service ? "Public Networking" tab ? copy Railway domain
4. Use these URLs for environment variables and linking services

**Testing connectivity:**
- Backend health: `curl https://<backend-url>/health`
- Frontend: Navigate to `https://<frontend-url>` in browser
- If backend returns error, check Railway logs for startup errors

# Stock Screener Deployment Guide

This guide provides instructions for deploying the Stock Screener application to **Google Cloud Run** as separate services for the backend and frontend.

## 📋 Prerequisites
- A Google Cloud Project with Billing enabled.
- `gcloud` CLI installed and authenticated.
- Upstox/Zerodha API keys.

---

## 🚀 Step 1: Deploy the Backend
The backend must be deployed first to generate the URL needed by the frontend.

```bash
# Run from the project root
gcloud run deploy stock-screener-backend \
  --source . \
  --dockerfile backend/Dockerfile \
  --region us-central1 \
  --allow-unauthenticated
```

**Important:** After deployment, copy the **Service URL** provided by Google (e.g., `https://stock-screener-backend-xxxxx.a.run.app`).

---

## 🚀 Step 2: Deploy the Frontend
Replace `YOUR_BACKEND_URL` with the URL you copied in the previous step.

```bash
# Run from the project root
gcloud run deploy stock-screener-frontend \
  --source frontend \
  --dockerfile frontend/Dockerfile \
  --region us-central1 \
  --set-build-envs VITE_API_URL=https://YOUR_BACKEND_URL/api \
  --allow-unauthenticated
```

---

## ⚠️ Critical Notes for production

### 1. Persistence (Statelessness)
Google Cloud Run services are **stateless**. This means any changes made to `data/master.csv` or other files inside the container **will be lost** when the service restarts or scales down.
- **Recommendation:** Migrate data storage to a database like **Google Cloud SQL (PostgreSQL)** or **Firestore**.

### 2. Secret Management
Currently, credentials are read from `config.yaml`. For production:
- Use **Google Secret Manager** to store API keys.
- Mount secrets as environment variables in Cloud Run.
- Update `backend/config.py` to prioritize environment variables over the YAML file.

### 3. API Redirect URIs
Ensure that the Redirect URIs in your Upstox and Zerodha developer portals are updated to point to your deployed frontend URL.

---

## 🛠️ Local Development
If you want to run the app locally using the Docker setup:

```bash
# Build and run the entire stack (if using docker-compose)
docker-compose up --build
```

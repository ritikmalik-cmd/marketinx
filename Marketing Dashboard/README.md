# 📊 Marketing Dashboard

A comprehensive Streamlit-based analytics dashboard for Zoho CRM leads with multi-dimensional filtering, real-time data visualization, and lead owner performance tracking.

## Features

✨ **Dashboard Features:**
- 📈 Overview tab with lead distribution charts
- 👤 Lead Owner analytics with status breakdown
- 📋 Lead Status analysis with owner/source filters
- 🌐 Lead Source performance tracking
- 📊 Complete data table with advanced filtering
- 📅 Date range filtering (This Week, Last 30/90 Days, All Time, Custom)
- ⚡ Intelligent caching for 30,000+ leads
- 🔍 Multi-dimensional filtering across all sections

## Setup Instructions

### 1. Clone and Install Dependencies

```bash
git clone https://github.com/navneet-xmonks/cmsforxmonks.git
cd "Marketing Dashboard"
python -m venv .venv
```

On Windows:
```powershell
.\.venv\Scripts\activate
pip install -r requirements.txt
```

On macOS/Linux:
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Credentials

Create `.streamlit/secrets.toml` with your Zoho CRM credentials:

```toml
ZOHO_CLIENT_ID = "your-client-id"
ZOHO_CLIENT_SECRET = "your-client-secret"
ZOHO_REFRESH_TOKEN = "your-refresh-token"
ZOHO_REDIRECT_URI = "http://localhost:7860"
```

### 3. Run Locally

```bash
streamlit run dashboard.py
```

The app will be available at `http://localhost:8501`

---

## Deployment to Streamlit Cloud

### Quick Deploy (Recommended)

1. **Push code to GitHub:**
   ```bash
   git add .
   git commit -m "Deploy to Streamlit Cloud"
   git push origin main
   ```

2. **Deploy on Streamlit Cloud:**
   - Go to https://share.streamlit.io
   - Sign in with GitHub
   - Select your repository: `cmsforxmonks`
   - Set folder path to: `Marketing Dashboard`
   - Set main file to: `dashboard.py`
   - Click "Deploy"

3. **Add Secrets:**
   - In Streamlit Cloud dashboard, go to "Settings" → "Secrets"
   - Add your Zoho credentials:
     ```toml
     ZOHO_CLIENT_ID = "your-client-id"
     ZOHO_CLIENT_SECRET = "your-client-secret"
     ZOHO_REFRESH_TOKEN = "your-refresh-token"
     ```

### Alternative Deployments

**Heroku:**
```bash
heroku create your-app-name
git push heroku main
```

**Docker:**
```bash
docker build -t marketing-dashboard .
docker run -p 8501:8501 marketing-dashboard
```

---

## Performance Metrics

- ⚡ **Initial Load:** 2-3 minutes (30,000+ leads cached)
- 🔄 **Cache Duration:** 1 hour for leads, 30 minutes for tokens
- ⚙️ **API Fields:** 11 optimized fields (40-50% payload reduction)
- 🎯 **Filter Updates:** <1 second (client-side filtering)

## API Integration

- **Service:** Zoho CRM v2 API
- **Endpoint:** https://www.zohoapis.com/crm/v2/Leads
- **Auth:** OAuth 2.0 Refresh Token Flow
- **Pagination:** 200 records per page with automatic pagination

## Troubleshooting

**Q: Leads not loading?**
- Check that Zoho credentials are correct in `.streamlit/secrets.toml`
- Verify API connection: Look for error messages in terminal

**Q: Dashboard is slow?**
- Cache is limited to 1 hour - try refreshing after changes
- Check internet connection for API latency

**Q: Secrets not loading?**
- Ensure `.streamlit/secrets.toml` has correct path and format
- Streamlit Cloud requires secrets in web UI, not file

## Architecture

```
┌─────────────────────────────────────┐
│     Streamlit UI (Web App)          │
├─────────────────────────────────────┤
│  • Date Range Filters               │
│  • Multi-Select Filters             │
│  • Interactive Charts (Plotly)      │
└────────────────┬────────────────────┘
                 │
         ┌───────▼────────┐
         │ Caching Layer  │
         │ (1hr leads)    │
         └───────┬────────┘
                 │
         ┌───────▼────────────────┐
         │ Zoho CRM API v2        │
         │ OAuth 2.0 Auth         │
         └────────────────────────┘
```

## Support

For issues or questions:
1. Check error logs in terminal
2. Verify API credentials
3. Review `.streamlit/secrets.toml` configuration

---

**Last Updated:** November 2025
**Version:** 1.0

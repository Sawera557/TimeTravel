# Deploy TimeTravel Tasks to Vercel
This guide shows how to deploy the Flask task manager to Vercel for free hosting.
## Prerequisites
- Vercel account (free)
- GitHub account
- Your project pushed to GitHub
## Step 1: Prepare for Vercel
Vercel expects a different structure for Python apps. Create these files:
### vercel.json
`json
{
  \"version\": 2,
  \"builds\": [
    {
      \"src\": \"app.py\",
      \"use\": \"@vercel/python\"
    }
  ],
  \"routes\": [
    {
      \"src\": \"/(.*)\",
      \"dest\": \"app.py\"
    }
  ]
}
`
### api/app.py (Vercel expects this structure)
Move your pp.py to pi/app.py and modify it for Vercel:
`python
# api/app.py
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import json
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import uuid4
from datetime import datetime, timezone
app = Flask(__name__, 
    static_folder='../static',
    template_folder='../templates')
CORS(app)
# ... rest of your code ...
# Vercel requires this for serverless functions
def handler(event, context):
    return app(event, context)
if __name__ == \"__main__\":
    app.run()
`
### requirements.txt
`
flask
flask-cors
`
## Step 2: Deploy to Vercel
### Option A: Vercel CLI
`ash
# Install Vercel CLI
npm install -g vercel
# Login
vercel login
# Deploy
vercel
# Follow prompts:
# - Link to existing project or create new
# - Set project name
# - Choose Python runtime
# - Deploy
`
### Option B: GitHub Integration
1. Push code to GitHub
2. Go to [vercel.com](https://vercel.com)
3. Click "New Project"
4. Import from GitHub
5. Configure:
   - **Framework Preset**: Other
   - **Root Directory**: ./ (leave default)
   - **Build Command**: Leave empty
   - **Output Directory**: Leave empty
## Step 3: Environment Variables
In Vercel dashboard, add environment variables:
`
FLASK_ENV=production
`
## Step 4: File Structure for Vercel
Your project should look like this:
`
FlaskProject/
+-- api/
¦   +-- app.py              # Modified Flask app
+-- static/
¦   +-- css/
¦   ¦   +-- app.css
¦   +-- js/
¦       +-- app.js
+-- templates/
¦   +-- index.html
+-- data/
¦   +-- task_state.json     # Will be created
+-- vercel.json             # Vercel config
+-- requirements.txt
+-- README.md
`
## Step 5: Modify app.py for Vercel
Update your pp.py (now pi/app.py) for Vercel:
`python
# Add this at the top
import os
# Change this line:
STORE_PATH = Path(__file__).with_name(\"data\").joinpath(\"task_state.json\")
# To this:
if os.getenv('VERCEL'):
    # Vercel environment
    STORE_PATH = Path('/tmp/task_state.json')
else:
    # Local development
    STORE_PATH = Path(__file__).parent.parent / 'data' / 'task_state.json'
# Add Vercel handler at the end:
def handler(event, context):
    from flask import Request
    from werkzeug.test import EnvironBuilder
    # Convert Vercel event to Flask request
    builder = EnvironBuilder(
        method=event['httpMethod'],
        path=event['path'],
        query_string=event.get('queryStringParameters', {}),
        headers=event.get('headers', {}),
        data=json.dumps(event.get('body', {})) if event.get('body') else None
    )
    with app.test_request_context(builder.get_environ()):
        response = app.full_dispatch_request()
        return {
            'statusCode': response.status_code,
            'headers': dict(response.headers),
            'body': response.get_data(as_text=True)
        }
`
## Step 6: Test Deployment
After deployment:
1. **Check health endpoint**: https://your-app.vercel.app/health
2. **Open main app**: https://your-app.vercel.app/
3. **Test functionality**: Create, edit, delete tasks
4. **Test time travel**: Undo/redo should work
## Common Issues
### Static files not loading
- Ensure static_folder='../static' in Flask app config
- Check file paths in templates
### Data not persisting
- Vercel serverless functions are stateless
- Data resets on each deployment
- For persistence, use Vercel KV or external database
### CORS issues
- Vercel handles CORS automatically
- Remove manual CORS setup if issues occur
### Build failures
- Check ercel.json syntax
- Ensure equirements.txt has correct dependencies
- Check Vercel function logs
## Alternative: Vercel + Supabase
For persistent data, combine Vercel with Supabase:
1. Deploy Flask app to Vercel (as above)
2. Set up Supabase database
3. Add Supabase environment variables to Vercel
4. Use the Supabase integration from SUPABASE_INTEGRATION.md
## Cost
- **Free tier**: 100GB bandwidth, 1000 serverless function invocations/month
- **Hobby plan**: /month for higher limits
- **Pro plan**: /month for unlimited
## Monitoring
- Check Vercel dashboard for function usage
- Monitor error logs in Vercel dashboard
- Set up uptime monitoring for your app
## Next Steps
1. Set up custom domain
2. Add analytics
3. Configure CI/CD
4. Add error tracking
5. Set up monitoring alerts


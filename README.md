# Data agent: JSON/Excel -> CSV -> shareable dashboard

## Run locally
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=sk-ant-...   # optional; without it, simple rules pick the charts
    streamlit run app.py

## Auto-update from Excel
1. Upload your Excel file to Google Sheets (File > Import).
2. Sheet: File > Share > Publish to web > choose the sheet and "CSV" > Publish. Copy the link.
3. In the app, choose "Google Sheet" and paste the link. It re-reads every 60 seconds.
Edit the sheet and the dashboard follows. (Keep editing in Google Sheets, or re-upload from Excel.)

## Share with anyone
1. Put these files in a GitHub repo.
2. share.streamlit.io > New app > pick the repo, main file app.py.
3. In Settings > Secrets add: ANTHROPIC_API_KEY = "sk-ant-..."
4. Send the public URL. It opens on any device, no account needed.

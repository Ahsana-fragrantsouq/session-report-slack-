import os
import requests
from datetime import datetime, timedelta
from flask import Flask, request, jsonify

app = Flask(__name__)

SHOPIFY_STORE_DOMAIN = os.environ.get("SHOPIFY_STORE_DOMAIN")
SHOPIFY_ADMIN_API_TOKEN = os.environ.get("SHOPIFY_ADMIN_API_TOKEN")
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")

# for API access token
CLIENT_ID     = os.getenv("SHOPIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SHOPIFY_CLIENT_SECRET")
REDIRECT_URI  = os.getenv("SHOPIFY_REDIRECT_URI")  # e.g. https://your-render-url.com/auth/callback



def fetch_sessions_report():
    """Fetch yesterday's sessions by landing page from Shopify Analytics."""
    print(f"[{datetime.utcnow()}] Fetching sessions report from Shopify...", flush=True)
    print(f"[{datetime.utcnow()}] Store domain: {SHOPIFY_STORE_DOMAIN}", flush=True)

    query = """
    {
      shopifyqlQuery(query: "FROM sessions SHOW sessions BY landing_page_path SINCE -1d UNTIL today ORDER BY sessions DESC LIMIT 20") {
        parseErrors { code message }
        tableData {
          rowData
          columns { name dataType }
        }
      }
    }
    """
    url = f"https://{SHOPIFY_STORE_DOMAIN}/admin/api/2025-01/graphql.json"
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": SHOPIFY_ADMIN_API_TOKEN,
    }

    print(f"[{datetime.utcnow()}] Sending GraphQL request to: {url}", flush=True)
    resp = requests.post(url, json={"query": query}, headers=headers, timeout=15)
    print(f"[{datetime.utcnow()}] Shopify response status: {resp.status_code}", flush=True)
    resp.raise_for_status()

    data = resp.json()
    print(f"[{datetime.utcnow()}] Shopify response received successfully.", flush=True)
    return data


def build_slack_message(data):
    """Format the session data into a Slack message."""
    print(f"[{datetime.utcnow()}] Building Slack message...", flush=True)

    yesterday_str = (datetime.utcnow() - timedelta(days=1)).strftime("%d %b %Y")

    table = data["data"]["shopifyqlQuery"]["tableData"]
    columns = [c["name"] for c in table["columns"]]
    rows = table["rowData"]

    print(f"[{datetime.utcnow()}] Total rows received: {len(rows)}", flush=True)

    path_idx = columns.index("landing_page_path")
    sessions_idx = columns.index("sessions")

    lines = [
        f"*📊 Today's Sessions — {yesterday_str}*",
        "",
    ]

    for i, row in enumerate(rows):
        path = row[path_idx]
        count = row[sessions_idx]

        if path == "/":
            label = "🏠 Homepage"
        elif "/products/" in path:
            name = path.split("/products/")[-1].replace("-", " ").title()
            label = f"🛍 {name}"
        elif "/collections/" in path:
            name = path.split("/collections/")[-1].replace("-", " ").title()
            label = f"📂 {name}"
        else:
            label = f"📄 {path}"

        print(f"[{datetime.utcnow()}] Row {i+1}: {label} → {count} sessions", flush=True)
        lines.append(f"• {label}: *{count}*")

    lines.append("")
    lines.append(f"_Generated at {datetime.utcnow().strftime('%H:%M')} UTC_")

    print(f"[{datetime.utcnow()}] Slack message built successfully.", flush=True)
    return "\n".join(lines)


def send_slack_report():
    """Fetch report and post to Slack."""
    print(f"[{datetime.utcnow()}] ========== Starting daily session report ==========", flush=True)

    data = fetch_sessions_report()

    errors = data["data"]["shopifyqlQuery"]["parseErrors"]
    if errors:
        print(f"[{datetime.utcnow()}] ShopifyQL parse errors: {errors}", flush=True)
        return "ShopifyQL error", 500

    print(f"[{datetime.utcnow()}] No ShopifyQL errors. Proceeding...", flush=True)

    message = build_slack_message(data)

    print(f"[{datetime.utcnow()}] Sending message to Slack...", flush=True)
    response = requests.post(SLACK_WEBHOOK_URL, json={"text": message}, timeout=10)
    print(f"[{datetime.utcnow()}] Slack response status: {response.status_code}", flush=True)
    response.raise_for_status()

    print(f"[{datetime.utcnow()}] ========== Daily session report sent successfully ==========", flush=True)
    return "OK"


@app.route("/trigger/daily-session-report", methods=["GET", "POST"])
def daily_session_report():
    print(f"[{datetime.utcnow()}] /trigger/daily-session-report endpoint hit.", flush=True)
    try:
        result = send_slack_report()
        return result, 200
    except Exception as e:
        print(f"[{datetime.utcnow()}] ERROR: {e}", flush=True)
        return f"Error: {str(e)}", 500


@app.route("/health", methods=["GET"])
def health():
    print(f"[{datetime.utcnow()}] Health check OK.", flush=True)
    return "OK", 200

# API access token
@app.route("/auth", methods=["GET"])
def auth():
    shop = request.args.get("shop", SHOPIFY_STORE_DOMAIN)
    scopes = "read_analytics"
    auth_url = (
        f"https://{shop}/admin/oauth/authorize"
        f"?client_id={CLIENT_ID}"
        f"&scope={scopes}"
        f"&redirect_uri={REDIRECT_URI}"
    )
    from flask import redirect
    return redirect(auth_url)


@app.route("/auth/callback", methods=["GET"])
def auth_callback():
    code = request.args.get("code")
    shop = request.args.get("shop")  # ← use shop from callback params

    if not code:
        return "No code received", 400
    if not shop:
        return "No shop received", 400

    token_url = f"https://{shop}/admin/oauth/access_token"
    response = requests.post(token_url, json={
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code":          code
    })

    print(f"🔑 Token exchange response: {response.status_code} — {response.text}", flush=True)

    token_data = response.json()
    access_token = token_data.get("access_token")
    print(f"🔑 NEW ACCESS TOKEN: {access_token}", flush=True)

    return jsonify({
        "access_token": access_token,
        "shop": shop,
        "message": "Copy this token and update SHOPIFY_TOKEN in your airtable service on Render!"
    })

def fetch_sessions_report():
    print(f"[{datetime.utcnow()}] Fetching sessions report from Shopify...", flush=True)
    print(f"[{datetime.utcnow()}] Store domain: {SHOPIFY_STORE_DOMAIN}", flush=True)

    query = """
    {
      shopifyqlQuery(query: "FROM sessions SHOW sessions BY landing_page_path SINCE -1d UNTIL today ORDER BY sessions DESC LIMIT 20") {
        parseErrors { code message }
        tableData {
          rowData
          columns { name dataType }
        }
      }
    }
    """
    url = f"https://{SHOPIFY_STORE_DOMAIN}/admin/api/2024-01/graphql.json"
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": SHOPIFY_ADMIN_API_TOKEN,
    }

    print(f"[{datetime.utcnow()}] Sending GraphQL request to: {url}", flush=True)
    resp = requests.post(url, json={"query": query}, headers=headers, timeout=15)
    print(f"[{datetime.utcnow()}] Shopify response status: {resp.status_code}", flush=True)
    
    # ADD THIS LINE:
    print(f"[{datetime.utcnow()}] Shopify response body: {resp.text}", flush=True)
    
    resp.raise_for_status()
    data = resp.json()
    print(f"[{datetime.utcnow()}] Shopify response received successfully.", flush=True)
    return data

if __name__ == "__main__":
    app.run(debug=False)

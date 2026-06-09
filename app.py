import os
import requests
from datetime import datetime, timedelta, timezone
from collections import Counter
from flask import Flask, request, jsonify, redirect

app = Flask(__name__)

SHOPIFY_STORE_DOMAIN = os.environ.get("SHOPIFY_STORE_DOMAIN")
SHOPIFY_ADMIN_API_TOKEN = os.environ.get("SHOPIFY_ADMIN_API_TOKEN")
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")

CLIENT_ID     = os.getenv("SHOPIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SHOPIFY_CLIENT_SECRET")
REDIRECT_URI  = os.getenv("SHOPIFY_REDIRECT_URI")


def fetch_sessions_report():
    """Fetch yesterday's visitor data using Shopify REST API."""
    print(f"[{datetime.utcnow()}] Fetching sessions report from Shopify...", flush=True)
    print(f"[{datetime.utcnow()}] Store domain: {SHOPIFY_STORE_DOMAIN}", flush=True)

    yesterday = (datetime.now(timezone.utc) - timedelta(days=1))
    date_min = yesterday.strftime("%Y-%m-%dT00:00:00Z")
    date_max = yesterday.strftime("%Y-%m-%dT23:59:59Z")
    date_str = yesterday.strftime("%d %b %Y")

    headers = {
        "X-Shopify-Access-Token": SHOPIFY_ADMIN_API_TOKEN,
        "Content-Type": "application/json",
    }

    # Fetch yesterday's orders with landing_site info
    url = (
        f"https://{SHOPIFY_STORE_DOMAIN}/admin/api/2025-01/orders.json"
        f"?status=any&created_at_min={date_min}&created_at_max={date_max}"
        f"&limit=250&fields=id,landing_site,referring_site"
    )

    print(f"[{datetime.utcnow()}] Fetching orders from: {url}", flush=True)
    resp = requests.get(url, headers=headers, timeout=15)
    print(f"[{datetime.utcnow()}] Response status: {resp.status_code}", flush=True)
    print(f"[{datetime.utcnow()}] Response body (first 300 chars): {resp.text[:300]}", flush=True)
    resp.raise_for_status()

    orders = resp.json().get("orders", [])
    print(f"[{datetime.utcnow()}] Total orders yesterday: {len(orders)}", flush=True)

    return orders, date_str


def build_slack_message(orders, date_str):
    """Format the orders data into a Slack message showing landing pages."""
    print(f"[{datetime.utcnow()}] Building Slack message...", flush=True)

    # Count landing pages from orders
    landing_counts = Counter()
    for order in orders:
        site = order.get("landing_site") or "/"
        # Normalize: strip query strings
        path = site.split("?")[0]
        landing_counts[path] += 1

    lines = [
        f"*📊 Today's Sessions — {date_str}*",
        f"_Based on {len(orders)} orders placed yesterday_",
        "",
    ]

    if not landing_counts:
        lines.append("_No orders found for yesterday._")
    else:
        for i, (path, count) in enumerate(landing_counts.most_common(20)):
            if path == "/" or path == "":
                label = "🏠 Homepage"
            elif "/products/" in path:
                name = path.split("/products/")[-1].replace("-", " ").title()
                label = f"🛍 {name}"
            elif "/collections/" in path:
                name = path.split("/collections/")[-1].replace("-", " ").title()
                label = f"📂 {name}"
            else:
                label = f"📄 {path}"
            print(f"[{datetime.utcnow()}] Row {i+1}: {label} → {count}", flush=True)
            lines.append(f"• {label}: *{count}*")

    lines.append("")
    lines.append(f"_Generated at {datetime.utcnow().strftime('%H:%M')} UTC_")

    print(f"[{datetime.utcnow()}] Slack message built successfully.", flush=True)
    return "\n".join(lines)


def send_slack_report():
    """Fetch report and post to Slack."""
    print(f"[{datetime.utcnow()}] ========== Starting daily session report ==========", flush=True)

    orders, date_str = fetch_sessions_report()
    message = build_slack_message(orders, date_str)

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


@app.route("/auth", methods=["GET"])
def auth():
    shop = request.args.get("shop", SHOPIFY_STORE_DOMAIN)
    scopes = "read_analytics,read_orders"
    auth_url = (
        f"https://{shop}/admin/oauth/authorize"
        f"?client_id={CLIENT_ID}"
        f"&scope={scopes}"
        f"&redirect_uri={REDIRECT_URI}"
    )
    return redirect(auth_url)


@app.route("/auth/callback", methods=["GET"])
def auth_callback():
    code = request.args.get("code")
    shop = request.args.get("shop")

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

    print(f"[{datetime.utcnow()}] Token exchange response: {response.status_code} — {response.text}", flush=True)

    token_data = response.json()
    access_token = token_data.get("access_token")
    print(f"[{datetime.utcnow()}] NEW ACCESS TOKEN: {access_token}", flush=True)

    return jsonify({
        "access_token": access_token,
        "shop": shop,
        "message": "Copy this token and set it as SHOPIFY_ADMIN_API_TOKEN on Render!"
    })


if __name__ == "__main__":
    app.run(debug=False)

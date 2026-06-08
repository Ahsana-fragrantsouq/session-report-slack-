import os
import requests
from datetime import datetime, timedelta
from flask import Flask

app = Flask(__name__)

SHOPIFY_STORE_DOMAIN = os.environ.get("SHOPIFY_STORE_DOMAIN")
SHOPIFY_ADMIN_API_TOKEN = os.environ.get("SHOPIFY_ADMIN_API_TOKEN")
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")


def fetch_sessions_report():
    """Fetch yesterday's sessions by landing page from Shopify Analytics."""
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
    resp = requests.post(url, json={"query": query}, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()


def build_slack_message(data):
    """Format the session data into a Slack message."""
    yesterday_str = (datetime.utcnow() - timedelta(days=1)).strftime("%d %b %Y")

    table = data["data"]["shopifyqlQuery"]["tableData"]
    columns = [c["name"] for c in table["columns"]]
    rows = table["rowData"]

    path_idx = columns.index("landing_page_path")
    sessions_idx = columns.index("sessions")

    lines = [
        f"*📊 Today's Sessions — {yesterday_str}*",
        "",
    ]

    for row in rows:
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

        lines.append(f"• {label}: *{count}*")

    lines.append("")
    lines.append(f"_Generated at {datetime.utcnow().strftime('%H:%M')} UTC_")

    return "\n".join(lines)


def send_slack_report():
    """Fetch report and post to Slack."""
    print(f"[{datetime.utcnow()}] Starting daily session report...", flush=True)

    data = fetch_sessions_report()

    errors = data["data"]["shopifyqlQuery"]["parseErrors"]
    if errors:
        print(f"ShopifyQL errors: {errors}", flush=True)
        return "ShopifyQL error", 500

    message = build_slack_message(data)

    response = requests.post(SLACK_WEBHOOK_URL, json={"text": message}, timeout=10)
    response.raise_for_status()

    print("Daily session report sent to Slack successfully.", flush=True)
    return "OK"


@app.route("/trigger/daily-session-report", methods=["GET", "POST"])
def daily_session_report():
    try:
        result = send_slack_report()
        return result, 200
    except Exception as e:
        print(f"Error: {e}", flush=True)
        return f"Error: {str(e)}", 500


@app.route("/health", methods=["GET"])
def health():
    return "OK", 200


if __name__ == "__main__":
    app.run(debug=False)

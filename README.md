# shopify-slack-reports

Sends a daily Shopify session report to a Slack channel every morning.

## Setup

### 1. Slack Incoming Webhook
1. Go to https://api.slack.com/apps → Create New App → From Scratch
2. Enable **Incoming Webhooks**
3. Click **Add New Webhook to Workspace**
4. Select the `#session` channel
5. Copy the webhook URL

### 2. Shopify Admin API Token
Your existing token works **if** it has `read_analytics` scope.
To check/add: Shopify Admin → Settings → Apps → Develop apps → your app → Configuration → add `read_analytics`

### 3. Deploy to Render
1. Push this folder to a new GitHub repo
2. Go to https://render.com → New Web Service → connect repo
3. Add these environment variables:
   - `SHOPIFY_STORE_DOMAIN` = `fragrantsouq.myshopify.com`
   - `SHOPIFY_ADMIN_API_TOKEN` = your token
   - `SLACK_WEBHOOK_URL` = webhook URL from Step 1

### 4. Schedule with cron-job.org (free)
1. Go to https://cron-job.org → sign up
2. New cronjob:
   - URL: `https://shopify-slack-reports.onrender.com/trigger/daily-session-report`
   - Schedule: `30 2 * * *`  ← 2:30 AM UTC = 8:00 AM IST
   - Method: GET

## Sample Slack Output

```
📊 Today's Sessions — 07 Jun 2025

• 🏠 Homepage: 19
• 🛍 Arabian Oud Madawi Gold Edition 100 Ml Edp Unisex Perfume: 4
• 🛍 Tiziana Terenzi Luna Collection Andromeda 100 Ml: 4
• 🛍 Sospiro Vibranto 100 Ml Edp Unisex Perfume: 3
• 🛍 Swiss Arabian Sawalef Scent Of Seduction 80 Ml: 2
...

_Generated at 02:30 UTC_
```

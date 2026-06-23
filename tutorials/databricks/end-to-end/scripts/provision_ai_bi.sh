#!/usr/bin/env bash
# Stage 12 — provision the AI/BI dashboard + Genie space VIA CLI (not the UI).
# Both read the governed silverline.gold.portfolio_metrics Metric View, so a dashboard
# tile and a Genie answer can never disagree. Idempotency note: re-running CREATES NEW
# objects (lakeview/genie have no upsert) — delete the old ones first if you re-run.
#
# Requires: the `free` CLI profile (OAuth) + .env (DATABRICKS_HOST, DATABRICKS_WAREHOUSE_ID).
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a
PROFILE="${DATABRICKS_PROFILE:-free}"

echo "==> Creating Lakeview dashboard from dashboards/portfolio_dashboard.lvdash.json"
DASH_ID=$(databricks --profile "$PROFILE" lakeview create \
  --display-name "Silverline Capital — Portfolio (governed metrics)" \
  --warehouse-id "$DATABRICKS_WAREHOUSE_ID" \
  --serialized-dashboard "$(cat dashboards/portfolio_dashboard.lvdash.json)" \
  -o json | uv run python -c "import sys,json; print(json.load(sys.stdin)['dashboard_id'])")
echo "    dashboard_id=$DASH_ID"

echo "==> Publishing (embed warehouse credentials so viewers can render it)"
databricks --profile "$PROFILE" lakeview publish "$DASH_ID" \
  --warehouse-id "$DATABRICKS_WAREHOUSE_ID" --embed-credentials >/dev/null
echo "    published → $DATABRICKS_HOST/dashboardsv3/$DASH_ID/published"

echo "==> Creating Genie space from dashboards/genie_space.json"
SPACE_ID=$(databricks --profile "$PROFILE" genie create-space "$DATABRICKS_WAREHOUSE_ID" \
  "$(cat dashboards/genie_space.json)" \
  --title "Silverline Capital — Portfolio Genie" \
  --description "Natural-language Q&A over the governed portfolio_metrics Metric View (Silverline Capital)." \
  -o json | uv run python -c "import sys,json; print(json.load(sys.stdin)['space_id'])")
echo "    space_id=$SPACE_ID → $DATABRICKS_HOST/genie/rooms/$SPACE_ID"

echo
echo "Done. Open the dashboard + Genie space above. Both query MEASURE() over"
echo "silverline.gold.portfolio_metrics — dashboard == Genie == gold."

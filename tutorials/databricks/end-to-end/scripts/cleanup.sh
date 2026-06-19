#!/usr/bin/env bash
# Tear down EVERYTHING this tutorial created and return the workspace to its fresh $0
# Free Edition state. Idempotent — every step ignores "not found", so it's safe to re-run.
#
#   ./scripts/cleanup.sh [--dry-run] [--yes]
#     --dry-run   show what would be deleted; delete nothing
#     --yes       skip the confirmation prompt
#
# ⚠️ DESTRUCTIVE + IRREVERSIBLE. Keeps the shared Starter Warehouse (pre-existing). Does NOT
# touch your personal AWS account — see the reminder printed at the end.
#
# Resource names default to the tutorial's conventions; override any via env (e.g. CATALOG=foo).
set -uo pipefail
cd "$(dirname "$0")/.."                       # tutorial root
[ -f .env ] && { set -a; . ./.env; set +a; }  # DATABRICKS_HOST, LAKEBASE_USER, LAKEBASE_UC_CATALOG, …

PROFILE="${DATABRICKS_PROFILE:-free}"
DRY=0; YES=0
for a in "$@"; do case "$a" in
  --dry-run) DRY=1 ;; --yes|-y) YES=1 ;;
  *) echo "unknown arg: $a (use --dry-run / --yes)"; exit 2 ;;
esac; done

# --- what gets removed (override via env if you renamed anything) ---
CATALOG="${CATALOG:-silverline}"
CDF_CATALOG="${CDF_CATALOG:-silverline_cdf}"
LAKEBASE_UC_CATALOG="${LAKEBASE_UC_CATALOG:-lakebase_silverline_oltp}"
LAKEBASE_PROJECT="${LAKEBASE_PROJECT:-silverline-oltp}"
SP_NAME="${SP_NAME:-silverline-data-api}"
SECRET_SCOPE="${SECRET_SCOPE:-silverline}"
PIPELINE_NAME="${PIPELINE_NAME:-silverline-medallion-sdp}"
JOB_NAMES=("silverline-dbt-job" "silverline-notebook-job")
DASHBOARD_TITLE="${DASHBOARD_TITLE:-Silverline Capital — Portfolio (governed metrics)}"
GENIE_TITLE="${GENIE_TITLE:-Silverline Capital — Portfolio Genie}"
USER_EMAIL="${LAKEBASE_USER:-$(databricks --profile "$PROFILE" current-user me -o json 2>/dev/null \
  | python3 -c 'import sys,json;print(json.load(sys.stdin).get("userName",""))' 2>/dev/null)}"
WORKSPACE_DIR="${WORKSPACE_DIR:-/Workspace/Users/${USER_EMAIL}/SilverAIWolf}"

dbx(){ databricks --profile "$PROFILE" "$@"; }
say(){ printf '\n\033[1m• %s\033[0m\n' "$*"; }
run(){ if [ "$DRY" = 1 ]; then echo "  [dry-run] $*"; else eval "$@" >/dev/null 2>&1 && echo "  ✓ removed" || echo "  – not found / skipped"; fi; }

# Extract ids from a `-o json` list by matching a field == value. Handles array or
# {dashboards|spaces|jobs|statuses|Resources}, and names nested under settings (jobs).
pick(){ python3 -c '
import sys, json
field, val, idkey = sys.argv[1], sys.argv[2], sys.argv[3]
try: data = json.load(sys.stdin)
except Exception: sys.exit(0)
if isinstance(data, dict):
    for k in ("dashboards","spaces","jobs","statuses","Resources","resources"):
        if isinstance(data.get(k), list): data = data[k]; break
    else: data = [data]
for o in (data if isinstance(data, list) else []):
    s = o.get("settings", {}) if isinstance(o, dict) else {}
    name = o.get(field) or s.get(field)
    if name == val:
        i = o.get(idkey) or s.get(idkey)
        if i is not None: print(i)
' "$@"; }

cat <<EOF
About to tear down the tutorial from: ${DATABRICKS_HOST:-(profile $PROFILE)}
  • UC catalogs : $CATALOG (CASCADE) · $CDF_CATALOG · $LAKEBASE_UC_CATALOG
  • Lakebase    : project $LAKEBASE_PROJECT (serverless Postgres)
  • Identity    : service principal $SP_NAME · secret scope $SECRET_SCOPE
  • Compute     : pipeline $PIPELINE_NAME · jobs ${JOB_NAMES[*]}
  • Analytics   : dashboard "$DASHBOARD_TITLE" · Genie "$GENIE_TITLE"
  • Notebooks   : $WORKSPACE_DIR
  KEEPS the shared Starter Warehouse. Does NOT touch your AWS account.
EOF
[ "$DRY" = 1 ] && echo "
DRY RUN — nothing will be deleted."
if [ "$YES" != 1 ] && [ "$DRY" != 1 ]; then
  read -r -p $'\nThis is irreversible. Type "destroy" to proceed: ' c
  [ "$c" = "destroy" ] || { echo "aborted."; exit 1; }
fi

say "1/9 Workspace notebooks"
run "dbx workspace delete \"$WORKSPACE_DIR\" --recursive"

say "2/9 AI/BI dashboard"
for id in $(dbx lakeview list -o json 2>/dev/null | pick display_name "$DASHBOARD_TITLE" dashboard_id); do run "dbx lakeview trash \"$id\""; done

say "3/9 Genie space"
for id in $(dbx genie list-spaces -o json 2>/dev/null | pick title "$GENIE_TITLE" space_id); do run "dbx genie trash-space \"$id\""; done

say "4/9 Jobs"
for jn in "${JOB_NAMES[@]}"; do
  for id in $(dbx jobs list -o json 2>/dev/null | pick name "$jn" job_id); do run "dbx jobs delete \"$id\""; done
done

say "5/9 SDP pipeline"
for id in $(dbx pipelines list-pipelines -o json 2>/dev/null | pick name "$PIPELINE_NAME" pipeline_id); do run "dbx pipelines delete \"$id\""; done

say "6/9 UC catalogs (force-drops schemas/tables/views/volume/metric-view/functions)"
for c in "$LAKEBASE_UC_CATALOG" "$CDF_CATALOG" "$CATALOG"; do run "dbx catalogs delete \"$c\" --force"; done

say "7/9 Lakebase project (serverless Postgres — also drops the WAL slot + triggers)"
run "dbx postgres delete-project \"$LAKEBASE_PROJECT\""
[ "$DRY" = 1 ] || echo "  ℹ️  Lakebase keeps the slug '$LAKEBASE_PROJECT' reserved for a retention window after delete (see the re-provisioning note below)."

say "8/9 Service principal"
for id in $(dbx service-principals list -o json 2>/dev/null | pick displayName "$SP_NAME" id); do run "dbx service-principals delete \"$id\""; done

say "9/9 Secret scope"
run "dbx secrets delete-scope \"$SECRET_SCOPE\""

cat <<EOF

✅ Teardown complete — workspace should be back to its fresh \$0 state (Starter Warehouse kept).

⚠️ Re-provisioning the SAME Lakebase name isn't immediate. Lakebase SOFT-deletes the project and
   RESERVES its slug ($LAKEBASE_PROJECT) for a retention window (observed several hours+). Re-running
   the provision stage with the same name fails with "slug already exists" until the slug frees. To
   re-provision sooner, use a different name, e.g.:
     databricks postgres create-project ${LAKEBASE_PROJECT}-2 --json '{"spec":{"pg_version":17}}'
   then set that name when you continue the tutorial (provision stage).

⚠️ NOT removed (outside Databricks — do these yourself):
  • If you ran the optional CDF / AWS-quickstart step, the S3 bucket + IAM role live in YOUR
    AWS account as a CloudFormation stack and bill to AWS (not Databricks). First Disable CDF
    in the Lakebase UI (if still on), then delete that CloudFormation stack in the AWS console.
  • Local artifacts: rm -rf .venv dbt/target dbt/logs
EOF

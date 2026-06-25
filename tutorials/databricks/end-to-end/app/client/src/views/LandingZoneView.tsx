import Callout from "../Callout";
import TutorialGuide from "../TutorialGuide";

export default function LandingZoneView() {
  return (
    <div className="stack">
      <Callout icon="🗂️">
        <p>
          <strong>Unity Catalog</strong> is Databricks' governance layer — a three-level namespace
          (catalog → schema → table/volume) with access control, lineage, and data discovery built in.
          You own one catalog: <code>silverline</code>, with three schemas that mirror the medallion
          architecture (<code>bronze</code> / <code>silver</code> / <code>gold</code>) and a{" "}
          <strong>managed volume</strong> for files.
        </p>
        <p>
          <strong>Managed</strong> means Databricks owns the storage lifecycle — drop the volume and
          the files are deleted. <strong>External</strong> means your own cloud bucket — drop the volume
          registration and the files are kept. For Free Edition we use managed volumes (no cloud account
          needed).
        </p>
      </Callout>

      <TutorialGuide title="What to do in stage 02 — create the Unity Catalog landing zone">
        <ol>
          <li>
            In the workspace, open the <strong>SQL editor</strong> (left sidebar → SQL Editor).
          </li>
          <li>
            Run this block to create the catalog and medallion schemas (idempotent — safe to re-run):
            <pre className="erd">{`CREATE CATALOG IF NOT EXISTS silverline
  COMMENT 'Shared landing zone for all tutorial phases.';
CREATE SCHEMA IF NOT EXISTS silverline.bronze COMMENT 'Raw / ingested';
CREATE SCHEMA IF NOT EXISTS silverline.silver COMMENT 'Cleaned / current-state';
CREATE SCHEMA IF NOT EXISTS silverline.gold   COMMENT 'Business / serving';`}</pre>
          </li>
          <li>
            Create the managed volume for seed files and contract PDFs:
            <pre className="erd">{`CREATE VOLUME IF NOT EXISTS silverline.bronze.files
  COMMENT 'Managed volume — seed files + contract PDFs for the RAG track.';`}</pre>
          </li>
          <li>
            Verify your work:
            <pre className="erd">{`SHOW SCHEMAS IN silverline;      -- expect bronze, silver, gold
SHOW VOLUMES IN silverline.bronze; -- expect files`}</pre>
          </li>
          <li>
            Browse to <strong>Catalog Explorer</strong> in the UI (left sidebar → Catalog) to see{" "}
            <code>silverline</code> and its schemas — this is what Unity Catalog looks like.
          </li>
        </ol>
      </TutorialGuide>
    </div>
  );
}

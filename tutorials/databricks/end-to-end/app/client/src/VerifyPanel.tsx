import { gql } from "@apollo/client";
import { useLazyQuery } from "@apollo/client/react";

const VERIFY = gql`
  query VerifyStage($id: String!) {
    verifyStage(id: $id) {
      passed
      checks {
        name
        passed
        detail
      }
    }
  }
`;

type Check = { name: string; passed: boolean; detail: string };
type VerifyResult = { passed: boolean; checks: Check[] };

export default function VerifyPanel({
  stageId,
  nextLabel,
  onVerified,
}: {
  stageId: string;
  nextLabel: string;
  onVerified: () => void;
}) {
  const [run, { loading, data, error, called }] = useLazyQuery<{ verifyStage: VerifyResult }>(
    VERIFY,
    { fetchPolicy: "no-cache" },
  );

  const result = data?.verifyStage;
  const allPassed = result?.passed ?? false;

  return (
    <div className="verify-wrap">
      {/* run / retry button */}
      {(!called || !allPassed) && (
        <button className="verify-btn" onClick={() => run({ variables: { id: stageId } })} disabled={loading}>
          {loading ? (
            <><span className="spin" />Checking your work…</>
          ) : called ? (
            "↺ Re-check"
          ) : (
            "✓ Verify your work"
          )}
        </button>
      )}

      {error && <p className="err verify-err">Check failed: {error.message}</p>}

      {result && (
        <div className="verify-results">
          {result.checks.map((c, i) => (
            <div key={i} className={`vcheck ${c.passed ? "pass" : "fail"}`}>
              <span className="vic">{c.passed ? "✓" : "✗"}</span>
              <div className="vtext">
                <span className="vname">{c.name}</span>
                <span className="vdetail">{c.detail}</span>
              </div>
            </div>
          ))}

          {allPassed && (
            <button className="verify-advance" onClick={onVerified}>
              All checks passed — continue to {nextLabel} →
            </button>
          )}
        </div>
      )}
    </div>
  );
}

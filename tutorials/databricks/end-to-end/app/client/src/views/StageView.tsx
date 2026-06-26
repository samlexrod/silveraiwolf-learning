import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import TableBrowserWidget from "../widgets/TableBrowserWidget";
import LiveFeedWidget from "../widgets/LiveFeedWidget";

type Callout = { icon: string; body: string };
type Section = { heading: string; body: string };
type Content = { callout?: Callout | null; sections: Section[] };

export type StageConfigView = {
  id: string;
  phase: string;
  label: string;
  icon: string;
  title: string;
  special?: string | null;
  hasVerify: boolean;
  widgets: string[];
  content?: Content | null;
};

const WIDGETS: Record<string, React.FC> = {
  "table-browser": TableBrowserWidget,
  "live-feed":     LiveFeedWidget,
};

export default function StageView({ stage }: { stage: StageConfigView }) {
  const { content, widgets } = stage;

  return (
    <div className="stack">
      {content?.callout && (
        <div className="callout">
          <span className="callout-icon">{content.callout.icon}</span>
          <div className="callout-body">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{content.callout.body}</ReactMarkdown>
          </div>
        </div>
      )}

      {content?.sections.map((section, i) => (
        <div key={i} className="t-guide">
          <div className="t-guide-head">{section.heading}</div>
          <div className="t-guide-body">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{section.body}</ReactMarkdown>
          </div>
        </div>
      ))}

      {widgets.map((w) => {
        const Widget = WIDGETS[w];
        return Widget ? <Widget key={w} /> : null;
      })}
    </div>
  );
}

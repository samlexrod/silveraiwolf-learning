import { useEffect, useState } from "react";

type Props = {
  /** Selector for the container where selections are allowed (e.g. ".content"). */
  within: string;
  onSend: (text: string) => void;
};

export default function SelectionTooltip({ within, onSend }: Props) {
  const [pos, setPos] = useState<{ x: number; y: number } | null>(null);
  const [text, setText] = useState("");

  useEffect(() => {
    const onMouseUp = () => {
      const sel = window.getSelection();
      if (!sel || sel.isCollapsed) { setPos(null); return; }
      const raw = sel.toString().trim();
      if (raw.length < 6) { setPos(null); return; }

      // only trigger inside one of the target containers (supports comma-separated selectors)
      const range = sel.getRangeAt(0);
      const containers = Array.from(document.querySelectorAll(within));
      if (!containers.some((c) => c.contains(range.commonAncestorContainer))) {
        setPos(null);
        return;
      }

      const rect = range.getBoundingClientRect();
      // getBoundingClientRect() is viewport-relative; `position: fixed` needs viewport coords (no scrollY)
      setPos({ x: rect.left + rect.width / 2, y: rect.top });
      setText(raw);
    };

    const onMouseDown = (e: MouseEvent) => {
      if ((e.target as Element).closest(".sel-tooltip")) return;
      setPos(null);
    };

    document.addEventListener("mouseup", onMouseUp);
    document.addEventListener("mousedown", onMouseDown);
    return () => {
      document.removeEventListener("mouseup", onMouseUp);
      document.removeEventListener("mousedown", onMouseDown);
    };
  }, [within]);

  if (!pos) return null;

  return (
    <div
      className="sel-tooltip"
      style={{ left: pos.x, top: pos.y - 44 }}
      // prevent mousedown from clearing the selection before the click fires
      onMouseDown={(e) => e.preventDefault()}
    >
      <button
        onClick={() => {
          onSend(text);
          window.getSelection()?.removeAllRanges();
          setPos(null);
        }}
      >
        💬 Ask Claude about this
      </button>
    </div>
  );
}

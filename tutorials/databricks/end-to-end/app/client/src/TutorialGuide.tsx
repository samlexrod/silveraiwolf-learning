type Props = {
  title: string;
  children: React.ReactNode;
};

export default function TutorialGuide({ title, children }: Props) {
  return (
    <div className="t-guide">
      <div className="t-guide-head">{title}</div>
      <div className="t-guide-body">{children}</div>
    </div>
  );
}

type Props = {
  icon?: string;
  children: React.ReactNode;
};

export default function Callout({ icon, children }: Props) {
  return (
    <div className="callout">
      {icon && <span className="callout-icon">{icon}</span>}
      <div className="callout-body">{children}</div>
    </div>
  );
}

interface PlaceholderProps {
  title: string;
  description: string;
  note?: string;
}

export function PagePlaceholder({ title, description, note }: PlaceholderProps) {
  return (
    <section className="page">
      <header className="page-header">
        <h1>{title}</h1>
        <p>{description}</p>
      </header>

      <div className="placeholder-card">
        <h3>{title}</h3>
        <p>{description}</p>
        <span className="phase">Planned for a later implementation phase ({note ?? "P1-P3"}).</span>
      </div>
    </section>
  );
}
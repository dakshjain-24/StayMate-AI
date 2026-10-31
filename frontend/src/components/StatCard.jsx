export default function StatCard({ label, value, note }) {
  return (
    <article className="stat-card">
      <span>{label}</span>
      <strong>{value ?? "—"}</strong>
      <small>{note}</small>
    </article>
  );
}

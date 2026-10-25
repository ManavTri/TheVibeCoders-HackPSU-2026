export function SectionCard({ title, subtitle, action, children, className = '' }) {
  return (
    <section className={`rounded-2xl border border-neutral-800 bg-[#0b0e12] p-5 shadow-sm ${className}`}>
      <div className="mb-5 flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-neutral-200">{title}</p>
          {subtitle ? <p className="text-xs text-neutral-500">{subtitle}</p> : null}
        </div>
        {action ? <div>{action}</div> : null}
      </div>
      {children}
    </section>
  )
}

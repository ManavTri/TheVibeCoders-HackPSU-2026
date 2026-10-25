const toneStyles = {
  amber: 'border-[#e7b66b]/35 bg-[#171712] text-neutral-100 ring-[#e7b66b]/20',
  emerald: 'border-[#83a99b]/35 bg-[#101c18] text-neutral-100 ring-[#83a99b]/20',
  cyan: 'border-[#a9c8dc]/35 bg-[#101923] text-neutral-100 ring-[#a9c8dc]/20',
  violet: 'border-[#8492a6]/35 bg-[#121821] text-neutral-100 ring-[#8492a6]/20',
}

export function StatCard({ title, value, change, detail, tone = 'cyan', tooltip }) {
  return (
    <div className={`h-full rounded-2xl border p-5 shadow-sm ring-1 ${toneStyles[tone]}`}>
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm text-neutral-300">{title}</p>
        <div className="group relative z-[60] inline-flex">
          <span
            className={`rounded-full border px-2 py-1 text-[10px] font-medium uppercase tracking-[0.2em] ${
              tone === 'amber'
                ? 'border-[#e7b66b]/40 bg-[#e7b66b]/10 text-[#f4d192]'
                : tone === 'emerald'
                  ? 'border-[#83a99b]/40 bg-[#83a99b]/10 text-[#b9d6c8]'
                  : tone === 'cyan'
                    ? 'border-[#a9c8dc]/40 bg-[#a9c8dc]/10 text-[#d5ebff]'
                    : 'border-[#8492a6]/40 bg-[#8492a6]/10 text-[#dce5f0]'
            }`}
          >
            {change}
          </span>
          {tooltip ? (
            <span className="pointer-events-none absolute left-1/2 top-full z-[90] mt-2 w-52 -translate-x-1/2 rounded-xl border border-[#dfe4da] bg-[#fffefc] px-2.5 py-2 text-left text-[11px] leading-5 text-[#1f2a33] opacity-0 shadow-lg shadow-slate-900/10 transition-all duration-150 ease-out group-hover:opacity-100 group-focus-within:opacity-100">
              {tooltip}
            </span>
          ) : null}
        </div>
      </div>
      <p className="mt-5 text-3xl font-semibold tracking-tight text-white">{value}</p>
      <p className="mt-2 text-sm text-neutral-400">{detail}</p>
    </div>
  )
}

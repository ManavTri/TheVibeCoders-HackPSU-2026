import muniLogo from '../assets/FinanceTool2026Fall.png'

const navItems = [
  { name: 'Dashboard', icon: '⌂' },
  { name: 'Documents', icon: '▣' },
  { name: 'Financial Insights', icon: '◫' },
  { name: 'AI Chat', icon: '✦' },
]

const utilityItems = [{ name: 'Settings', icon: '⚙' }]

export function Sidebar({ activePage, onChange, aidSnapshot = '—' }) {
  return (
    <aside className="w-full border-b border-[#1d232b] bg-[#0a0d11] p-5 backdrop-blur xl:w-72 xl:border-b-0 xl:border-r">
      <div className="mb-8 flex items-center gap-3">
        <img src={muniLogo} alt="Muni" className="h-11 w-36 rounded-xl bg-white object-cover shadow-sm" />
      </div>

      <nav className="space-y-2">
        {navItems.map((item) => {
          const isActive = activePage === item.name

          return (
            <button
              key={item.name}
              type="button"
              onClick={() => onChange(item.name)}
              className={`flex w-full items-center justify-between rounded-xl px-4 py-3 text-left text-sm font-medium transition-all ${
                isActive
                  ? 'bg-[#12191f] text-white ring-1 ring-[#2b333d]'
                  : 'text-slate-300 hover:bg-[#111821] hover:text-white'
              }`}
            >
              <span className="flex items-center gap-3">
                <span className="text-lg">{item.icon}</span>
                {item.name}
              </span>
              {isActive ? <span className="h-2.5 w-2.5 rounded-full bg-white" /> : null}
            </button>
          )
        })}
      </nav>

      <div className="mt-8 space-y-2 border-t border-[#1d232b] pt-4">
        {utilityItems.map((item) => {
          const isActive = activePage === item.name

          return (
            <button
              key={item.name}
              type="button"
              onClick={() => onChange(item.name)}
              className={`flex w-full items-center justify-between rounded-xl px-4 py-3 text-left text-sm font-medium transition-all ${
                isActive
                  ? 'bg-[#12191f] text-white ring-1 ring-[#2b333d]'
                  : 'text-slate-300 hover:bg-[#111821] hover:text-white'
              }`}
            >
              <span className="flex items-center gap-3">
                <span className="text-lg">{item.icon}</span>
                {item.name}
              </span>
              {isActive ? <span className="h-2.5 w-2.5 rounded-full bg-white" /> : null}
            </button>
          )
        })}
      </div>

      <div className="mt-8 rounded-3xl border border-[#1d232b] bg-[#0f141a] p-4 shadow-sm">
        <p className="text-xs uppercase tracking-[0.2em] text-slate-300">Aid snapshot</p>
        <p className="mt-3 text-2xl font-semibold text-white">{aidSnapshot}</p>
        <p className="mt-1 text-sm text-slate-400">From active award letters</p>
      </div>
    </aside>
  )
}

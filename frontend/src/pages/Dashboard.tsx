import { Link } from 'react-router-dom'

export function Dashboard() {
  return (
    <main className="content-page page-wrap">
      <div className="page-heading">
        <div><div className="eyebrow">YOUR MONEY, IN CONTEXT</div><h1>Good to see you.</h1><p>Bring your award letters and bills together for a clearer view.</p></div>
        <Link className="button button-primary" to="/upload">+ New document check</Link>
      </div>
      <section className="dashboard-grid">
        <article className="dashboard-feature">
          <div className="feature-art"><span className="feature-star">✳</span><div className="mini-paper"><b>$12,000</b><span>award amount</span><i>✓</i></div></div>
          <div className="eyebrow">START WITH A QUICK CHECK</div>
          <h2>Make the fine print<br />feel a little less fine.</h2>
          <p>Compare a scholarship, tuition bill, or program quote. We’ll point out details that may be worth confirming.</p>
          <Link className="text-link" to="/upload">Compare documents <span>→</span></Link>
        </article>
        <aside className="dashboard-side">
          <div className="eyebrow">HOW IT WORKS</div>
          <div className="how-item"><span>01</span><div><b>Add your documents</b><p>PDFs from your school, scholarship provider, or program.</p></div></div>
          <div className="how-item"><span>02</span><div><b>We look for mismatches</b><p>Amounts, terms, dates, and credit requirements.</p></div></div>
          <div className="how-item"><span>03</span><div><b>Get questions to ask</b><p>Know what to follow up on with your financial-aid office.</p></div></div>
          <div className="demo-callout"><span>✦</span><p>New here? Try the synthetic sample PDFs from our demo scenario.</p></div>
        </aside>
      </section>
      <footer className="site-footer"><span>ClearLedger © 2026</span><span>For planning support—not financial advice.</span><Link to="/">Back to home</Link></footer>
    </main>
  )
}

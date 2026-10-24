import { Link } from 'react-router-dom'

export function Landing() {
  return (
    <main className="landing page-wrap">
      <section className="hero">
        <div className="hero-copy">
          <div className="eyebrow hero-kicker"><span className="live-dot" /> CLARITY FOR YOUR CAMPUS MONEY</div>
          <h1>Make your money<br />make <span>sense.</span></h1>
          <p className="hero-subtitle">Scholarships, tuition bills, study-abroad costs. Bring the paperwork together and find the details worth a second look.</p>
          <div className="hero-actions">
            <Link className="button button-primary" to="/upload">Check my documents <span aria-hidden="true">↗</span></Link>
            <span className="privacy-note"><span aria-hidden="true">◈</span> Private by design. Your documents stay yours.</span>
          </div>
          <div className="hero-stats">
            <div><strong>01</strong><span>Upload your statements</span></div>
            <div><strong>02</strong><span>Compare the fine print</span></div>
            <div><strong>03</strong><span>Know what to ask next</span></div>
          </div>
        </div>
        <div className="hero-art" aria-label="Illustration of a student financial document review">
          <div className="art-orbit orbit-one" />
          <div className="art-orbit orbit-two" />
          <div className="art-spark spark-a">✳</div><div className="art-spark spark-b">✳</div>
          <div className="floating-tag tag-top"><span className="tag-check">✓</span><span><b>Scholarship</b><small>2026 award letter</small></span></div>
          <div className="paper-stack">
            <div className="paper-back"><i /><i /><i /></div>
            <div className="paper-front">
              <div className="paper-brand"><span>↗</span> CLEARLEDGER <small>STUDENT AWARD</small></div>
              <div className="paper-line short" /><div className="paper-line" />
              <div className="paper-amount">$12,000</div>
              <div className="paper-line medium" />
              <div className="paper-warning"><span>!</span><span><b>Term mismatch</b><small>Worth a closer look</small></span></div>
              <div className="paper-line" /><div className="paper-line short" />
            </div>
          </div>
          <div className="floating-tag tag-bottom"><span className="tag-alert">↕</span><span><b>Two details to review</b><small>We found something to check</small></span></div>
          <div className="art-caption">YOUR FINANCIAL PAPER TRAIL, untangled.</div>
        </div>
      </section>
      <section className="how-section">
        <div><div className="eyebrow">LESS GUESSING, MORE KNOWING</div><h2>Your documents.<br />One clearer picture.</h2></div>
        <p>We help you connect the dots between your financial documents—so you can spot questions early and make your next move with confidence.</p>
      </section>
      <footer className="site-footer"><span>ClearLedger © 2026</span><span>Built for students, with students.</span><Link to="/upload">Start a check →</Link></footer>
    </main>
  )
}

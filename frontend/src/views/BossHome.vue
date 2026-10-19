<template>
  <main class="boss-home">
    <header class="boss-nav">
      <router-link to="/" class="boss-logo" aria-label="BOSS home">
        <span class="boss-logo-mark">B</span>
        <span>BOSS</span>
      </router-link>
      <div class="boss-nav-center">India-context message review</div>
      <nav class="boss-nav-actions" aria-label="Primary navigation">
        <a href="#method">Method</a>
        <router-link to="/miroind" class="nav-cta">Review a message <span>↗</span></router-link>
      </nav>
    </header>

    <section class="boss-hero">
      <div class="hero-kicker"><span class="pulse-dot"></span> BOSS / INDIA-CONTEXT REVIEW</div>
      <div class="hero-grid">
        <div class="hero-copy">
          <h1>Know how it<br /><em>may</em> land.</h1>
          <p>
            Review a message through a defined Indian audience context before you publish.
            Find the risks, disagreements, and edits worth taking to real people.
          </p>
          <div class="hero-actions">
            <router-link to="/miroind" class="boss-button boss-button-primary">Review a message <span>→</span></router-link>
            <a href="#method" class="text-link">How it works <span>↓</span></a>
          </div>
        </div>
        <div class="hero-preview" aria-label="Example BOSS message review">
          <div class="preview-topline"><span>EXAMPLE REVIEW</span><span>01 / 03</span></div>
          <p class="preview-label">MESSAGE</p>
          <blockquote>“Hurry. Pay ₹999 today to unlock our best plan.”</blockquote>
          <div class="preview-context">
            <p class="preview-label">AUDIENCE CONTEXT</p>
            <strong>Rajasthan · Tier 2 · small shop owners</strong>
          </div>
          <div class="preview-finding">
            <span class="finding-mark">!</span>
            <div><p class="preview-label">BOSS FINDS</p><strong>Urgency may hide the terms.</strong><small>Add price conditions and proof.</small></div>
          </div>
        </div>
      </div>
      <div class="hero-meta">
        <span>Built for creators, founders, and teams in India</span>
        <span>Text-first · India-wide context · Offline-ready</span>
      </div>
    </section>

    <section id="method" class="method-section">
      <div class="section-intro">
        <div>
          <p class="section-number">01 / THE BOSS METHOD</p>
          <h2>Make the next<br /><span>decision clearer.</span></h2>
        </div>
        <p>
          Start with the message, then define the Indian context that matters: region,
          city tier, occupation, affordability, and local expression when relevant.
        </p>
      </div>
      <div class="method-grid">
        <article class="method-card featured-card">
          <span class="card-index">01</span>
          <div class="card-icon">01</div>
          <h3>Set the context</h3>
          <p>Describe the brand, the message, and the Indian audience situation you want to review.</p>
          <span class="card-caption">Brand + audience</span>
        </article>
        <article class="method-card">
          <span class="card-index">02</span>
          <div class="card-icon">02</div>
          <h3>Review the signal</h3>
          <p>See what may be misunderstood, questioned, or read differently across the audience context.</p>
          <span class="card-caption">Audience lenses</span>
        </article>
        <article class="method-card dark-card">
          <span class="card-index">03</span>
          <div class="card-icon">03</div>
          <h3>Choose the move</h3>
          <p>Take clear edits and validation questions into the next conversation with your audience.</p>
          <span class="card-caption">Practical next steps</span>
        </article>
      </div>
    </section>

    <section class="signal-section">
      <div class="signal-panel">
        <div class="signal-heading">
          <p class="section-number light-number">02 / WHAT BOSS SURFACES</p>
          <h2>What the review<br /><span>puts on the table.</span></h2>
        </div>
        <div class="signal-list">
          <div class="signal-row"><span>01</span><strong>Misreadings</strong><p>Where could the wording be unclear, salesy, or out of context?</p></div>
          <div class="signal-row"><span>02</span><strong>Trust gaps</strong><p>Which promises need terms, evidence, or a more careful claim?</p></div>
          <div class="signal-row"><span>03</span><strong>Audience differences</strong><p>Which people may respond differently because of their situation?</p></div>
          <div class="signal-row"><span>04</span><strong>Possible edits</strong><p>What can change without losing the brand’s voice?</p></div>
        </div>
      </div>
      <aside class="quote-card">
        <div class="quote-mark">“</div>
        <p>Not market evidence. A clearer starting point for the next real conversation.</p>
        <span>BOSS PRINCIPLE / 04</span>
      </aside>
    </section>

    <section class="launch-section">
      <div>
        <p class="section-number">03 / READY WHEN YOU ARE</p>
        <h2>Bring the message.<br /><span>Leave with a clearer next move.</span></h2>
      </div>
      <router-link to="/miroind" class="boss-button boss-button-primary">Create a review <span>↗</span></router-link>
    </section>

    <footer class="boss-footer">
      <div class="boss-logo small-logo"><span class="boss-logo-mark">B</span><span>BOSS</span></div>
      <span>Brand Outcome Signal System</span>
      <router-link to="/legacy">Original simulation workspace →</router-link>
      <span>© 2026 / Explore, then validate.</span>
    </footer>
  </main>
</template>

<style scoped>
:global(body) {
  background: #0b1110;
}

.boss-home {
  --ink: #e9efe6;
  --muted: #9aa89b;
  --line: rgba(219, 232, 215, .18);
  --lime: #d8b46a;
  --mint: #c6d9c8;
  --orange: #d8b46a;
  min-height: 100vh;
  overflow: hidden;
  color: var(--ink);
  background: #0b1110;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.boss-nav,
.hero-meta,
.hero-actions,
.boss-nav-actions,
.boss-footer,
.signal-row,
.launch-section {
  display: flex;
  align-items: center;
}

.boss-nav {
  justify-content: space-between;
  height: 78px;
  border-bottom: 1px solid var(--line);
  padding: 0 clamp(22px, 5vw, 76px);
}

.boss-logo {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: var(--ink);
  font-size: 18px;
  font-weight: 800;
  letter-spacing: .16em;
  text-decoration: none;
}

.boss-logo-mark {
  display: grid;
  width: 28px;
  height: 28px;
  place-items: center;
  color: #0b1110;
  background: var(--lime);
  font-size: 15px;
  font-weight: 900;
  letter-spacing: -.1em;
}

.boss-nav-center,
.boss-nav-actions a,
.hero-kicker,
.hero-meta,
.section-number,
.card-index,
.card-caption,
.float-label,
.core-label,
.core-index,
.signal-row > span,
.quote-card > span,
.boss-footer {
  font-size: 10px;
  font-weight: 800;
  letter-spacing: .15em;
  text-transform: uppercase;
}

.boss-nav-center { color: var(--muted); }
.boss-nav-actions { gap: 27px; }
.boss-nav-actions a { color: var(--muted); text-decoration: none; }
.boss-nav-actions a:hover { color: var(--lime); }
.boss-nav-actions .nav-cta { color: var(--lime); }
.boss-nav-actions .nav-cta span { margin-left: 5px; font-size: 14px; }

.boss-hero {
  position: relative;
  max-width: 1440px;
  margin: 0 auto;
  padding: clamp(50px, 8vw, 116px) clamp(22px, 9vw, 138px) 31px;
}

.hero-kicker { display: flex; align-items: center; gap: 10px; color: var(--lime); }
.pulse-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--lime); box-shadow: 0 0 0 5px rgba(216, 180, 106, .12); }
.hero-grid { display: grid; grid-template-columns: minmax(0, 1.08fr) minmax(370px, .92fr); align-items: center; gap: clamp(30px, 7vw, 130px); }
.hero-copy h1 { margin: 27px 0 26px; color: #f2f5ef; font-size: clamp(60px, 9vw, 138px); font-weight: 700; line-height: .84; letter-spacing: -.085em; }
.hero-copy h1 em { color: var(--lime); font-style: normal; }
.hero-copy > p { max-width: 480px; margin: 0; color: var(--muted); font-size: 16px; line-height: 1.65; }
.hero-actions { gap: 25px; margin-top: 34px; }
.boss-button { display: inline-flex; align-items: center; justify-content: space-between; gap: 27px; min-height: 52px; padding: 0 18px; border: 1px solid transparent; color: #0b1110; font-size: 11px; font-weight: 800; letter-spacing: .08em; text-decoration: none; text-transform: uppercase; transition: transform .2s, background .2s; }
.boss-button:hover { transform: translateY(-3px); }
.boss-button-primary { background: var(--lime); }
.boss-button-primary:hover { background: #e1fb84; }
.text-link { color: var(--muted); font-size: 12px; text-decoration: none; }
.text-link span { margin-left: 8px; color: var(--lime); }
.text-link:hover { color: var(--ink); }

.hero-preview { align-self: center; max-width: 480px; border: 1px solid rgba(219, 232, 215, .22); padding: 25px; background: #151e19; box-shadow: 18px 18px 0 rgba(216, 180, 106, .12); }
.preview-topline { display: flex; justify-content: space-between; padding-bottom: 17px; border-bottom: 1px solid rgba(219, 232, 215, .16); color: #7f9182; font-size: 10px; font-weight: 800; letter-spacing: .14em; }
.preview-label { margin: 0 0 9px; color: #8ca18e; font-size: 9px; font-weight: 800; letter-spacing: .13em; text-transform: uppercase; }
.hero-preview blockquote { margin: 27px 0 30px; border: 0; padding: 0; color: #f0f4eb; font-size: clamp(22px, 3vw, 31px); font-weight: 550; line-height: 1.14; letter-spacing: -.05em; }
.preview-context { padding: 15px 0; border-top: 1px solid rgba(219, 232, 215, .16); border-bottom: 1px solid rgba(219, 232, 215, .16); }
.preview-context strong { color: #c6d9c8; font-size: 13px; font-weight: 500; }
.preview-finding { display: flex; align-items: flex-start; gap: 13px; margin-top: 18px; }
.finding-mark { display: grid; width: 25px; height: 25px; flex: 0 0 auto; place-items: center; color: #111710; background: var(--lime); font-size: 14px; font-weight: 900; }
.preview-finding strong, .preview-finding small { display: block; }
.preview-finding strong { color: #f0f4eb; font-size: 14px; font-weight: 600; }
.preview-finding small { margin-top: 6px; color: #9aab9c; font-size: 12px; }
.visual-core { position: absolute; z-index: 2; top: 50%; left: 50%; display: flex; width: 235px; height: 235px; flex-direction: column; justify-content: space-between; transform: translate(-50%, -50%); border: 1px solid rgba(213, 242, 107, .7); border-radius: 50%; padding: 46px 40px 38px; background: radial-gradient(circle at 32% 24%, rgba(213, 242, 107, .2), transparent 38%), #18221d; box-shadow: 0 0 75px rgba(213, 242, 107, .09); }
.visual-core strong { color: #f2f5ef; font-size: 26px; line-height: .98; letter-spacing: -.06em; }
.core-label, .core-index { color: var(--lime); }
.core-index { align-self: flex-end; }
.orbit { position: absolute; top: 50%; left: 50%; border: 1px solid rgba(198, 232, 206, .16); border-radius: 50%; transform: translate(-50%, -50%) rotate(-25deg); }
.orbit-one { width: 330px; height: 190px; }
.orbit-two { width: 450px; height: 280px; transform: translate(-50%, -50%) rotate(32deg); border-color: rgba(213, 242, 107, .16); }
.float-label { position: absolute; z-index: 3; color: var(--muted); white-space: nowrap; }
.label-top { top: 22px; left: 8%; }
.label-right { top: 48%; right: -2%; color: var(--orange); }
.label-bottom { bottom: 25px; left: 19%; color: var(--mint); }
.hero-meta { justify-content: space-between; gap: 20px; margin-top: 40px; padding-top: 16px; border-top: 1px solid var(--line); color: #68766b; }

.method-section { padding: 115px clamp(22px, 9vw, 138px) 120px; color: #142019; background: #f0f4ec; }
.section-intro { display: grid; grid-template-columns: 1.1fr .8fr; gap: 60px; max-width: 1090px; margin: 0 auto 56px; }
.section-number { margin: 0 0 17px; color: #63816a; }
.section-intro h2, .signal-heading h2, .launch-section h2 { margin: 0; font-size: clamp(40px, 5vw, 72px); line-height: .92; letter-spacing: -.075em; }
.section-intro h2 span, .signal-heading h2 span, .launch-section h2 span { color: #6c9972; }
.section-intro > p { align-self: end; margin: 0; color: #627167; font-size: 15px; line-height: 1.7; }
.method-grid { display: grid; grid-template-columns: repeat(3, 1fr); max-width: 1090px; margin: 0 auto; border-top: 1px solid #cdd8cd; border-left: 1px solid #cdd8cd; }
.method-card { position: relative; min-height: 330px; border-right: 1px solid #cdd8cd; border-bottom: 1px solid #cdd8cd; padding: 27px; }
.featured-card { background: #dcefcf; }
.dark-card { color: #eef6ea; background: #183124; }
.card-index { color: #739278; }
.dark-card .card-index { color: #b6d990; }
.card-icon { margin: 50px 0 19px; color: #50785a; font-size: 44px; line-height: 1; }
.dark-card .card-icon { color: var(--lime); }
.method-card h3 { margin: 0 0 13px; font-size: 22px; letter-spacing: -.055em; }
.method-card p { max-width: 260px; margin: 0; color: #637268; font-size: 13px; line-height: 1.6; }
.dark-card p { color: #b8cabb; }
.card-caption { position: absolute; right: 27px; bottom: 27px; color: #77917a; }
.dark-card .card-caption { color: #a0be9a; }

.signal-section { display: grid; grid-template-columns: minmax(0, 1.3fr) minmax(270px, .7fr); gap: 18px; padding: 18px clamp(18px, 5vw, 76px) 120px; background: #f0f4ec; }
.signal-panel { display: grid; grid-template-columns: minmax(260px, .75fr) minmax(0, 1fr); gap: 40px; padding: clamp(28px, 5vw, 66px); color: #eff7ed; background: #183124; }
.light-number { color: #9cba8f; }
.signal-heading h2 { color: #f0f5ee; }
.signal-heading h2 span { color: var(--lime); }
.signal-list { border-top: 1px solid rgba(219, 232, 215, .2); }
.signal-row { display: grid; grid-template-columns: 28px minmax(115px, .55fr) 1fr; gap: 14px; padding: 16px 0; border-bottom: 1px solid rgba(219, 232, 215, .2); }
.signal-row > span { color: #96b18f; }
.signal-row strong { font-size: 14px; }
.signal-row p { margin: 0; color: #aabcae; font-size: 12px; line-height: 1.4; }
.quote-card { display: flex; min-height: 300px; flex-direction: column; justify-content: space-between; padding: 32px; color: #0c1810; background: var(--lime); }
.quote-mark { height: 40px; font-size: 64px; line-height: .8; }
.quote-card p { max-width: 300px; margin: 0; font-size: 27px; font-weight: 650; line-height: 1.08; letter-spacing: -.06em; }
.quote-card > span { color: #637b32; }

.launch-section { justify-content: space-between; gap: 30px; padding: 110px clamp(22px, 9vw, 138px); color: #eef4eb; background: #0b1110; }
.launch-section .section-number { color: #839b85; }
.launch-section .boss-button { flex: 0 0 auto; }
.boss-footer { flex-wrap: wrap; gap: 24px; justify-content: space-between; padding: 21px clamp(22px, 5vw, 76px); border-top: 1px solid var(--line); color: #758378; }
.small-logo { color: var(--ink); font-size: 13px; }
.small-logo .boss-logo-mark { width: 22px; height: 22px; font-size: 12px; }
.boss-footer a { color: var(--mint); text-decoration: none; }
.boss-footer a:hover { color: var(--lime); }

@media (max-width: 960px) {
  .boss-nav-center { display: none; }
  .hero-grid, .section-intro, .signal-section { grid-template-columns: 1fr; }
  .hero-visual { min-height: 350px; }
  .section-intro { gap: 22px; }
  .signal-panel { grid-template-columns: 1fr; }
}

@media (max-width: 650px) {
  .boss-nav { height: 68px; }
  .boss-nav-actions a:not(.nav-cta) { display: none; }
  .boss-nav-actions { gap: 0; }
  .hero-copy h1 { font-size: clamp(60px, 18vw, 100px); }
  .hero-actions, .hero-meta, .launch-section { align-items: flex-start; flex-direction: column; }
  .hero-meta { gap: 10px; }
  .method-grid { grid-template-columns: 1fr; }
  .method-card { min-height: 280px; }
  .signal-row { grid-template-columns: 25px 1fr; }
  .signal-row p { grid-column: 2; }
  .quote-card p { font-size: 24px; }
  .hero-visual { min-height: 300px; transform: scale(.82); transform-origin: center; }
  .label-right { right: -8%; }
}
</style>

<template>
  <main class="miroind-page">
    <header class="miroind-header">
      <div>
        <router-link class="back-link" to="/">← Back to BOSS</router-link>
        <div class="brand-lockup">
          <span class="brand-mark">B</span>
          <div>
            <p class="eyebrow">BOSS / INDIA MESSAGE LAB</p>
            <h1>BOSS</h1>
          </div>
        </div>
      </div>
      <div class="header-note">Synthetic review · validate with real people</div>
    </header>

    <section class="hero-card">
      <div>
        <p class="eyebrow accent">INDIA-CONTEXT MESSAGE REVIEW</p>
        <h2>Find what may be misunderstood before you publish.</h2>
        <p class="hero-copy">
          Describe your brand, paste a text asset, and define the audience you want to understand.
          Give BOSS the message and the audience context that matters. You will get focused risks,
          audience differences, and practical edits to take into your next review.
        </p>
      </div>
      <div class="principles">
        <span>Inspectable personas</span>
        <span>India-wide context signals</span>
        <span>No real platform posting</span>
      </div>
    </section>

    <div v-if="!report" class="workspace-grid">
      <form class="scenario-form panel" @submit.prevent="submitRun" novalidate>
        <div class="panel-heading">
          <div>
            <p class="eyebrow">01 / REVIEW INPUT</p>
            <h2>Review a message</h2>
          </div>
          <span class="required-note">* Required</span>
        </div>

        <fieldset>
          <legend>Brand or creator profile</legend>
          <div class="field-grid two-up">
            <label>
              <span>Name <b>*</b></span>
              <input v-model="form.brand.name" type="text" maxlength="120" placeholder="e.g. Nayi Disha" />
              <small v-if="errors['brand.name']" class="field-error">{{ errors['brand.name'] }}</small>
            </label>
            <label>
              <span>Tone <b>*</b></span>
              <input v-model="form.brand.tone" type="text" maxlength="160" placeholder="warm, clear, practical" />
              <small v-if="errors['brand.tone']" class="field-error">{{ errors['brand.tone'] }}</small>
            </label>
          </div>
          <label>
            <span>Positioning <b>*</b></span>
            <textarea v-model="form.brand.positioning" rows="2" maxlength="500" placeholder="What should people understand about you?" />
            <small v-if="errors['brand.positioning']" class="field-error">{{ errors['brand.positioning'] }}</small>
          </label>
          <label>
            <span>Relationship with the audience <b>*</b></span>
            <input v-model="form.brand.audience_relationship" type="text" maxlength="300" placeholder="a helpful partner" />
            <small v-if="errors['brand.audience_relationship']" class="field-error">{{ errors['brand.audience_relationship'] }}</small>
          </label>
          <div class="field-grid two-up">
            <label>
              <span>Red lines <em>(comma separated)</em></span>
              <input v-model="redLinesText" type="text" placeholder="no hidden fees, no hype" />
            </label>
            <label>
              <span>Preferred vocabulary <em>(comma separated)</em></span>
              <input v-model="preferredVocabularyText" type="text" placeholder="simple, useful, transparent" />
            </label>
          </div>
        </fieldset>

        <fieldset>
          <legend>Text asset</legend>
          <div class="field-grid two-up">
            <label>
              <span>Title <b>*</b></span>
              <input v-model="form.asset.title" type="text" maxlength="200" placeholder="Launch announcement" />
              <small v-if="errors['asset.title']" class="field-error">{{ errors['asset.title'] }}</small>
            </label>
            <label>
              <span>Primary asset language <em>(optional)</em></span>
              <input v-model="form.asset.language" type="text" maxlength="80" placeholder="Optional — English, Hindi, Marathi, or other" />
              <small v-if="errors['asset.language']" class="field-error">{{ errors['asset.language'] }}</small>
            </label>
          </div>
          <label>
            <span>Message or copy <b>*</b></span>
            <textarea v-model="form.asset.content" rows="8" maxlength="20000" placeholder="Paste the post, announcement, product message, or script you want to review." />
            <div class="field-footer">
              <small v-if="errors['asset.content']" class="field-error">{{ errors['asset.content'] }}</small>
              <small class="counter">{{ form.asset.content.length.toLocaleString() }} / 20,000</small>
            </div>
          </label>
        </fieldset>

        <fieldset>
            <legend>India audience context</legend>
          <div class="field-grid two-up">
            <label>
              <span>Region or state <b>*</b></span>
              <input v-model="form.audience.region" type="text" placeholder="Maharashtra" />
              <small v-if="errors['audience.region']" class="field-error">{{ errors['audience.region'] }}</small>
            </label>
            <label>
              <span>Local context signal <em>(optional)</em></span>
              <input v-model="form.audience.language" type="text" placeholder="Language, local phrasing, or context" />
              <small v-if="errors['audience.language']" class="field-error">{{ errors['audience.language'] }}</small>
            </label>
            <label>
              <span>Age band <b>*</b></span>
              <input v-model="form.audience.age_band" type="text" placeholder="25–34" />
              <small v-if="errors['audience.age_band']" class="field-error">{{ errors['audience.age_band'] }}</small>
            </label>
            <label>
              <span>Occupation <b>*</b></span>
              <input v-model="form.audience.occupation" type="text" placeholder="small business owner" />
              <small v-if="errors['audience.occupation']" class="field-error">{{ errors['audience.occupation'] }}</small>
            </label>
            <label>
              <span>City tier <b>*</b></span>
              <select v-model="form.audience.city_tier">
                <option value="tier_1">Tier 1</option>
                <option value="tier_2">Tier 2</option>
                <option value="tier_3">Tier 3 / smaller city</option>
                <option value="mixed">Mixed</option>
              </select>
              <small v-if="errors['audience.city_tier']" class="field-error">{{ errors['audience.city_tier'] }}</small>
            </label>
            <label>
              <span>Income band <b>*</b></span>
              <input v-model="form.audience.income_band" type="text" placeholder="middle" />
              <small v-if="errors['audience.income_band']" class="field-error">{{ errors['audience.income_band'] }}</small>
            </label>
          </div>
        </fieldset>

        <details class="advanced-settings">
          <summary>Review settings <span>Optional</span></summary>
          <fieldset>
          <legend>Output and audience depth</legend>
          <div class="field-grid three-up">
            <label>
              <span>Report output</span>
              <select v-model="form.config.report_language">
                <option value="en">English</option>
                <option value="hi">Hindi</option>
              </select>
            </label>
            <label>
              <span>Persona lenses</span>
              <input v-model.number="form.config.persona_count" type="number" min="4" max="10" step="1" />
              <small v-if="errors['config.persona_count']" class="field-error">{{ errors['config.persona_count'] }}</small>
            </label>
            <label>
              <span>Budget units</span>
              <input v-model.number="form.config.budget" type="number" min="1" step="1" />
              <small v-if="errors['config.budget']" class="field-error">{{ errors['config.budget'] }}</small>
            </label>
          </div>
          <label>
            <span>Review engine</span>
            <select v-model="form.config.analysis_mode">
              <option value="offline">Offline BOSS review</option>
              <option value="model">Configured model review</option>
            </select>
            <small class="settings-note">Model review uses the provider configured on the server. It never places credentials in the browser.</small>
            <small v-if="errors['config.analysis_mode']" class="field-error">{{ errors['config.analysis_mode'] }}</small>
          </label>
          <p class="helper-copy">These settings affect the review depth and are recorded with the result.</p>
          </fieldset>
        </details>

        <div v-if="formError" class="form-error" role="alert">{{ formError }}</div>
        <button class="primary-button" type="submit" :disabled="loading">
          <span v-if="loading" class="spinner" aria-hidden="true"></span>
          {{ loading ? 'Creating review…' : 'Create review →' }}
        </button>
      </form>

      <aside class="side-column">
        <section class="panel saved-run-panel">
          <p class="eyebrow">RETURN TO A REVIEW</p>
          <h2>Load saved review</h2>
          <p>Paste a saved review ID to reopen the exact result.</p>
          <div class="load-row">
            <input v-model="savedRunId" type="text" placeholder="miroind_…" @keyup.enter="loadSavedRun" />
            <button class="secondary-button" type="button" :disabled="loadingSaved" @click="loadSavedRun">
              {{ loadingSaved ? 'Loading…' : 'Load' }}
            </button>
          </div>
          <small v-if="loadError" class="field-error">{{ loadError }}</small>
        </section>
        <section class="panel guidance-panel">
          <p class="eyebrow">ONE IMPORTANT NOTE</p>
          <h2>Useful direction, not proof.</h2>
          <ul>
            <li>Use risks to form questions for real audience research.</li>
            <li>Compare disagreements instead of chasing a single score.</li>
            <li>Review any localised version with someone who knows the audience context.</li>
            <li>Do not upload private messages or personal data without permission.</li>
          </ul>
        </section>
      </aside>
    </div>

    <section v-else class="report-shell">
      <div class="report-toolbar">
        <div>
          <p class="eyebrow accent">RUN COMPLETE</p>
          <h2>BOSS / India message stress-test</h2>
          <p class="run-id">Run ID: <code>{{ runId }}</code></p>
        </div>
        <div class="toolbar-actions">
          <span v-if="copyStatus" class="copy-status" role="status">{{ copyStatus }}</span>
          <button class="secondary-button" type="button" @click="copyReport">Copy report</button>
          <button class="secondary-button" type="button" @click="downloadReport">Download .md</button>
          <button class="secondary-button" type="button" :disabled="loadingSaved" @click="reloadCurrentRun">
            {{ loadingSaved ? 'Loading…' : 'Reload saved result' }}
          </button>
          <button class="primary-button compact" type="button" @click="startNewRun">New review</button>
        </div>
      </div>

      <div class="report-disclaimer">
        <strong>Keep the human in the loop.</strong>
        This report contains deterministic synthetic hypotheses. It is not a survey, market truth, prediction, or substitute for real user research.
      </div>

      <section v-if="report.model_review?.status === 'completed'" class="model-review-card">
        <div class="model-review-heading">
          <div>
            <p class="eyebrow accent">MODEL REVIEW</p>
            <h3>Provider-backed second view</h3>
          </div>
          <span class="model-confidence">{{ report.model_review.confidence }} confidence</span>
        </div>
        <p class="model-assessment">{{ report.model_review.assessment }}</p>
        <div class="model-columns">
          <div>
            <p class="mini-label">Audience differences</p>
            <ul class="plain-list"><li v-for="(item, index) in report.model_review.audience_differences" :key="`model-audience-${index}`">{{ item }}</li></ul>
          </div>
          <div>
            <p class="mini-label">Model recommendations</p>
            <ul class="plain-list"><li v-for="(item, index) in report.model_review.recommendations" :key="`model-rec-${index}`">{{ item }}</li></ul>
          </div>
        </div>
      </section>

      <div class="report-overview">
        <article class="report-card impact-card">
          <p class="eyebrow">{{ report.labels?.overall_image_impact_direction || 'IMAGE IMPACT' }}</p>
          <strong class="impact-value" :class="`impact-${report.overall_image_impact_direction}`">
            {{ report.overall_image_impact_direction_label || report.overall_image_impact_direction }}
          </strong>
          <p>{{ report.scenario?.summary }}</p>
        </article>
        <article class="report-card">
          <p class="eyebrow">{{ report.labels?.audience_summary || 'AUDIENCE' }}</p>
          <p>{{ report.audience_summary?.summary }}</p>
          <div class="tag-list">
            <span>{{ report.audience_summary?.region }}</span>
            <span>{{ report.audience_summary?.city_tier }}</span>
            <span>{{ report.audience_summary?.occupation }}</span>
            <span>{{ report.audience_summary?.persona_count }} persona lenses</span>
          </div>
        </article>
      </div>

      <div class="report-grid">
        <section class="report-card wide-card">
          <div class="section-heading">
            <h3>{{ report.labels?.risk_points || 'Risk points' }}</h3>
            <span class="count-badge">{{ report.risk_points?.length || 0 }}</span>
          </div>
          <div v-if="report.risk_points?.length" class="risk-list">
            <article v-for="risk in report.risk_points" :key="risk.category" class="risk-card" :class="`severity-${risk.severity}`">
              <div class="risk-heading">
                <strong>{{ risk.label }}</strong>
                <span>{{ risk.severity }}</span>
              </div>
              <p>{{ risk.why_it_matters }}</p>
              <small>Signal: {{ risk.signals?.join(', ') }}</small>
              <blockquote>{{ risk.evidence }}</blockquote>
            </article>
          </div>
          <p v-else class="empty-copy">No configured risk signal was detected. That is not proof that the message is risk-free.</p>
        </section>

        <section class="report-card">
          <h3>{{ report.labels?.positive_reactions || 'Positive reactions' }}</h3>
          <ul class="plain-list"><li v-for="(item, index) in report.positive_reactions" :key="`positive-${index}`">{{ item }}</li></ul>
          <h3>{{ report.labels?.negative_reactions || 'Negative reactions' }}</h3>
          <ul class="plain-list"><li v-for="(item, index) in report.negative_reactions" :key="`negative-${index}`">{{ item }}</li></ul>
          <h3>{{ report.labels?.mixed_reactions || 'Mixed reactions' }}</h3>
          <ul class="plain-list"><li v-for="(item, index) in report.mixed_reactions" :key="`mixed-${index}`">{{ item }}</li></ul>
        </section>

        <section class="report-card wide-card">
          <div class="section-heading">
            <h3>{{ report.labels?.persona_reactions || 'Persona lenses' }}</h3>
            <span class="count-badge">{{ report.persona_reactions?.length || 0 }}</span>
          </div>
          <div class="persona-grid">
            <article v-for="persona in report.persona_reactions" :key="persona.persona_id" class="persona-card">
              <div class="persona-heading"><strong>{{ persona.label }}</strong><span :class="`impact-${persona.impact}`">{{ persona.impact_label }}</span></div>
              <p>{{ persona.research_lens }}</p>
              <p class="reaction-text">{{ persona.reaction }}</p>
              <small v-if="persona.concerns?.length">Checks: {{ persona.concerns.join(', ') }}</small>
            </article>
          </div>
        </section>

        <section class="report-card">
          <h3>{{ report.labels?.recommendations || 'Recommendations' }}</h3>
          <ol class="recommendation-list"><li v-for="(item, index) in report.recommendations" :key="`recommendation-${index}`">{{ item }}</li></ol>
          <h3>{{ report.labels?.disagreements || 'Disagreements' }}</h3>
          <ul class="plain-list"><li v-for="(item, index) in report.disagreements" :key="`disagreement-${index}`">{{ item }}</li></ul>
        </section>

        <section class="report-card">
          <h3>{{ report.labels?.rewrite_options || 'Rewrite options' }}</h3>
          <article v-for="rewrite in report.rewrite_options" :key="rewrite.option" class="rewrite-card">
            <strong>{{ rewrite.label }}</strong>
            <p>{{ rewrite.text }}</p>
            <small>{{ rewrite.rationale }}</small>
          </article>
        </section>

        <section class="report-card wide-card detail-card">
          <div class="detail-column">
            <h3>{{ report.labels?.misunderstandings || 'Potential misunderstandings' }}</h3>
            <ul class="plain-list"><li v-for="(item, index) in report.misunderstandings" :key="`misunderstanding-${index}`">{{ item }}</li></ul>
          </div>
          <div class="detail-column">
            <h3>{{ report.labels?.assumptions || 'Assumptions' }}</h3>
            <ul class="plain-list"><li v-for="(item, index) in report.assumptions" :key="`assumption-${index}`">{{ item }}</li></ul>
          </div>
          <div class="detail-column">
            <h3>{{ report.labels?.uncertainty || 'Uncertainty' }}</h3>
            <ul class="plain-list"><li v-for="(item, index) in report.uncertainty" :key="`uncertainty-${index}`">{{ item }}</li></ul>
          </div>
          <div class="detail-column">
            <h3>{{ report.labels?.limitations || 'Limitations' }}</h3>
            <ul class="plain-list"><li v-for="(item, index) in report.limitations" :key="`limitation-${index}`">{{ item }}</li></ul>
          </div>
        </section>

        <section class="report-card metadata-card wide-card">
          <h3>{{ report.labels?.usage_metadata || 'Usage metadata' }}</h3>
          <dl class="metadata-grid">
            <template v-for="(value, key) in report.usage_metadata" :key="key">
              <dt>{{ key.replaceAll('_', ' ') }}</dt>
              <dd>{{ formatMetadata(value) }}</dd>
            </template>
          </dl>
        </section>
      </div>
    </section>
  </main>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { createMiroIndRun, getMiroIndRun } from '../api/miroind'

const form = reactive({
  brand: {
    name: '',
    positioning: '',
    tone: '',
    audience_relationship: '',
  },
  asset: {
    type: 'text',
    title: '',
    content: '',
    language: 'en',
  },
  audience: {
    region: '',
    language: 'Not specified',
    age_band: '',
    occupation: '',
    city_tier: 'tier_2',
    income_band: '',
  },
  config: {
    report_language: 'en',
    interaction_format: 'short_post',
    persona_count: 6,
    budget: 20,
    analysis_mode: 'offline',
  },
})

const redLinesText = ref('')
const preferredVocabularyText = ref('')
const savedRunId = ref('')
const runId = ref('')
const report = ref(null)
const errors = ref({})
const formError = ref('')
const loadError = ref('')
const loading = ref(false)
const loadingSaved = ref(false)
const copyStatus = ref('')

const splitList = (value) => value.split(',').map((item) => item.trim()).filter(Boolean)

const payload = () => ({
  brand: {
    ...form.brand,
    red_lines: splitList(redLinesText.value),
    preferred_vocabulary: splitList(preferredVocabularyText.value),
  },
  asset: { ...form.asset },
  audience: { ...form.audience },
  config: { ...form.config },
})

const requiredFields = [
  ['brand.name', () => form.brand.name],
  ['brand.positioning', () => form.brand.positioning],
  ['brand.tone', () => form.brand.tone],
  ['brand.audience_relationship', () => form.brand.audience_relationship],
  ['asset.title', () => form.asset.title],
  ['asset.content', () => form.asset.content],
  ['audience.region', () => form.audience.region],
  ['audience.age_band', () => form.audience.age_band],
  ['audience.occupation', () => form.audience.occupation],
  ['audience.city_tier', () => form.audience.city_tier],
  ['audience.income_band', () => form.audience.income_band],
]

const validate = () => {
  const nextErrors = {}
  requiredFields.forEach(([key, getter]) => {
    if (!String(getter() || '').trim()) nextErrors[key] = 'This field is required.'
  })
  if (form.asset.content.length > 20000) nextErrors['asset.content'] = 'Use 20,000 characters or fewer.'
  if (!Number.isInteger(form.config.persona_count) || form.config.persona_count < 4 || form.config.persona_count > 10) {
    nextErrors['config.persona_count'] = 'Choose between 4 and 10 persona lenses.'
  }
  if (!Number.isInteger(form.config.budget) || form.config.budget < 1) nextErrors['config.budget'] = 'Budget must be at least 1.'
  errors.value = nextErrors
  return Object.keys(nextErrors).length === 0
}

const setRun = (record) => {
  runId.value = record.run_id
  savedRunId.value = record.run_id
  report.value = record.report
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

const submitRun = async () => {
  formError.value = ''
  loadError.value = ''
  if (!validate()) {
    formError.value = 'Please fix the highlighted fields before running the stress test.'
    return
  }
  loading.value = true
  try {
    const response = await createMiroIndRun(payload())
    setRun(response.data)
  } catch (error) {
    const fieldErrors = error.response?.data?.fields || {}
    errors.value = fieldErrors
    formError.value = error.response?.data?.error || error.message || 'The stress test could not be completed.'
  } finally {
    loading.value = false
  }
}

const loadSavedRun = async () => {
  const requestedId = savedRunId.value.trim()
  loadError.value = ''
  if (!requestedId) {
    loadError.value = 'Enter a run ID first.'
    return
  }
  loadingSaved.value = true
  try {
    const response = await getMiroIndRun(requestedId)
    setRun(response.data)
  } catch (error) {
    loadError.value = error.response?.data?.error || error.message || 'Saved run could not be loaded.'
  } finally {
    loadingSaved.value = false
  }
}

const reloadCurrentRun = async () => {
  savedRunId.value = runId.value
  await loadSavedRun()
}

const startNewRun = () => {
  report.value = null
  runId.value = ''
  errors.value = {}
  formError.value = ''
  loadError.value = ''
  copyStatus.value = ''
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

const markdownList = (title, items = []) => {
  if (!items.length) return `### ${title}\n\n_None reported._\n`
  return `### ${title}\n\n${items.map((item) => `- ${item}`).join('\n')}\n`
}

const buildReportMarkdown = () => {
  const current = report.value
  if (!current) return ''
  const scenario = current.scenario || {}
  const audience = current.audience_summary || {}
  const lines = [
    `# BOSS India-context message review`,
    `\n**Run ID:** ${runId.value}`,
    `\n## Summary\n\n- **Brand:** ${scenario.brand_name || 'Not provided'}`,
    `- **Message:** ${scenario.asset_title || 'Not provided'}`,
    `- **Audience:** ${audience.region || 'Not provided'} · ${audience.occupation || 'Not provided'} · ${audience.city_tier || 'Not provided'}`,
    `- **Overall direction:** ${current.overall_image_impact_direction_label || current.overall_image_impact_direction || 'Not provided'}`,
    `\n${scenario.summary || ''}\n`,
  ]
  if (current.model_review?.status === 'completed') {
    lines.push(`## Model review\n\n${current.model_review.assessment || ''}\n`)
    lines.push(markdownList('Model recommendations', current.model_review.recommendations))
    lines.push(markdownList('Audience differences', current.model_review.audience_differences))
  }
  lines.push(markdownList('Positive reactions', current.positive_reactions))
  lines.push(markdownList('Negative reactions', current.negative_reactions))
  lines.push(markdownList('Mixed reactions', current.mixed_reactions))
  lines.push(`### Risk points\n\n${(current.risk_points || []).length ? current.risk_points.map((risk) => `- **${risk.label} (${risk.severity})** — ${risk.why_it_matters}\n  - Evidence: ${risk.evidence}`).join('\n') : '_No configured risk signal was detected._'}\n`)
  lines.push(markdownList('Recommendations', current.recommendations))
  lines.push(`### Rewrite options\n\n${(current.rewrite_options || []).map((rewrite) => `#### ${rewrite.label}\n\n${rewrite.text}\n\n_${rewrite.rationale}_`).join('\n\n') || '_None reported._'}\n`)
  lines.push(markdownList('Potential misunderstandings', current.misunderstandings))
  lines.push(markdownList('Assumptions', current.assumptions))
  lines.push(markdownList('Uncertainty', current.uncertainty))
  lines.push(markdownList('Limitations', current.limitations))
  lines.push('\n---\n\n_Synthetic review, not market evidence. Validate with real people._\n')
  return lines.join('\n')
}

const copyReport = async () => {
  const markdown = buildReportMarkdown()
  if (!markdown) return
  try {
    await navigator.clipboard.writeText(markdown)
  } catch {
    const textarea = document.createElement('textarea')
    textarea.value = markdown
    textarea.setAttribute('readonly', '')
    textarea.style.position = 'fixed'
    textarea.style.opacity = '0'
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand('copy')
    textarea.remove()
  }
  copyStatus.value = 'Copied'
  window.setTimeout(() => { copyStatus.value = '' }, 1800)
}

const downloadReport = () => {
  const markdown = buildReportMarkdown()
  if (!markdown) return
  const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `boss-review-${runId.value || 'report'}.md`
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
  copyStatus.value = 'Downloaded'
  window.setTimeout(() => { copyStatus.value = '' }, 1800)
}

const formatMetadata = (value) => {
  if (Array.isArray(value)) return value.join(', ') || 'none'
  if (typeof value === 'boolean') return value ? 'yes' : 'no'
  return String(value)
}
</script>

<style scoped>
:global(body) {
  background: #f0f4ec;
}

.miroind-page {
  --ink: #142019;
  --muted: #627167;
  --line: #cdd8cd;
  --paper: #fdfef9;
  --green: #183124;
  --green-dark: #0b1110;
  --orange: #d5f26b;
  max-width: 1440px;
  min-height: 100vh;
  margin: 0 auto;
  padding: 28px 42px 80px;
  color: var(--ink);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.miroind-header,
.brand-lockup,
.toolbar-actions,
.load-row,
.risk-heading,
.persona-heading,
.section-heading,
.field-footer {
  display: flex;
  align-items: center;
}

.miroind-header {
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 28px;
}

.back-link {
  display: inline-block;
  margin-bottom: 18px;
  color: var(--muted);
  font-size: 12px;
  text-decoration: none;
}

.back-link:hover { color: var(--green); }

.brand-lockup { gap: 12px; }
.brand-mark {
  display: grid;
  width: 42px;
  height: 42px;
  place-items: center;
  color: #0b1110;
  background: var(--orange);
  font-size: 13px;
  font-weight: 800;
  letter-spacing: -0.08em;
}

.brand-lockup h1 { margin: 0; font-size: 26px; letter-spacing: -0.04em; }
.eyebrow { margin: 0 0 7px; color: var(--muted); font-size: 10px; font-weight: 800; letter-spacing: .14em; text-transform: uppercase; }
.accent { color: var(--orange); }
.header-note { align-self: flex-end; color: var(--muted); font-size: 12px; }

.hero-card {
  display: flex;
  justify-content: space-between;
  gap: 34px;
  margin-bottom: 24px;
  padding: 34px;
  color: #f8fbf5;
  background: var(--green);
}

.hero-card h2 { max-width: 700px; margin: 0 0 13px; font-size: clamp(29px, 4vw, 54px); line-height: 1.04; letter-spacing: -0.055em; }
.hero-copy { max-width: 700px; margin: 0; color: #cfddd4; font-size: 15px; line-height: 1.7; }
.principles { display: flex; min-width: 210px; flex-direction: column; justify-content: flex-end; gap: 9px; color: var(--orange); font-size: 12px; }
.principles span::before { content: "+"; margin-right: 7px; color: #fff; }

.workspace-grid { display: grid; grid-template-columns: minmax(0, 1.55fr) minmax(270px, .7fr); align-items: start; gap: 24px; }
.panel, .report-card { border: 1px solid var(--line); background: var(--paper); }
.panel { padding: 26px; }
.panel-heading { display: flex; justify-content: space-between; gap: 20px; margin-bottom: 24px; }
.panel-heading h2, .side-column h2, .report-toolbar h2 { margin: 0; font-size: 24px; letter-spacing: -0.04em; }
.required-note, em { color: var(--muted); font-size: 11px; font-style: normal; }

fieldset { margin: 0 0 26px; padding: 0 0 25px; border: 0; border-bottom: 1px solid var(--line); }
fieldset:last-of-type { margin-bottom: 20px; }
legend { margin-bottom: 14px; color: var(--green); font-size: 12px; font-weight: 800; letter-spacing: .06em; text-transform: uppercase; }
.field-grid { display: grid; gap: 16px; }
.two-up { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.three-up { grid-template-columns: 1.3fr .8fr .8fr; }
label { display: block; margin-bottom: 15px; }
.field-grid label { margin-bottom: 0; }
label > span { display: block; margin-bottom: 7px; color: #3d4b42; font-size: 12px; font-weight: 700; }
label b { color: var(--orange); }
input, textarea, select { width: 100%; border: 1px solid #c8ccc3; border-radius: 0; padding: 11px 12px; color: var(--ink); background: #fff; font: inherit; font-size: 13px; outline: 0; }
textarea { min-height: 80px; resize: vertical; }
input:focus, textarea:focus, select:focus { border-color: var(--green); box-shadow: 0 0 0 2px rgba(23, 107, 77, .12); }
.field-error { display: block; margin-top: 6px; color: #b33d2e; font-size: 11px; line-height: 1.4; }
.field-footer { justify-content: space-between; align-items: flex-start; gap: 12px; }
.counter { margin-top: 6px; color: var(--muted); font-size: 11px; white-space: nowrap; }
.helper-copy, .side-column p, .empty-copy { color: var(--muted); font-size: 12px; line-height: 1.6; }
.settings-note { display: block; margin-top: 6px; color: var(--muted); font-size: 11px; line-height: 1.5; }
.advanced-settings { margin-bottom: 22px; border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); }
.advanced-settings summary { display: flex; justify-content: space-between; padding: 16px 0; color: var(--green); cursor: pointer; font-size: 12px; font-weight: 800; list-style: none; text-transform: uppercase; }
.advanced-settings summary::-webkit-details-marker { display: none; }
.advanced-settings summary::after { content: '+'; color: var(--muted); font-size: 17px; font-weight: 400; }
.advanced-settings[open] summary::after { content: '−'; }
.advanced-settings summary span { margin-left: auto; margin-right: 12px; color: var(--muted); font-size: 10px; font-weight: 500; text-transform: none; }
.advanced-settings fieldset { margin-bottom: 0; padding-bottom: 20px; }
.form-error { margin: 10px 0 16px; border-left: 3px solid #b33d2e; padding: 10px 12px; color: #8f2e23; background: #fff0ec; font-size: 12px; }

button { border: 0; border-radius: 0; cursor: pointer; font: inherit; }
button:disabled { cursor: wait; opacity: .6; }
.primary-button, .secondary-button { min-height: 43px; padding: 0 17px; font-size: 12px; font-weight: 800; }
.primary-button { color: #0b1110; background: var(--orange); }
.primary-button:hover:not(:disabled) { background: #e2fb87; }
.primary-button.compact { min-height: 38px; }
.secondary-button { color: var(--green); border: 1px solid var(--green); background: transparent; }
.secondary-button:hover:not(:disabled) { color: #f5fbf1; background: var(--green); }
.spinner { display: inline-block; width: 11px; height: 11px; margin-right: 7px; border: 2px solid rgba(255,255,255,.4); border-top-color: #fff; border-radius: 50%; animation: spin .7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.side-column { display: grid; gap: 24px; }
.saved-run-panel h2, .guidance-panel h2 { margin-bottom: 11px; }
.load-row { align-items: stretch; margin-top: 18px; }
.load-row input { min-width: 0; }
.load-row .secondary-button { flex: 0 0 auto; }
.guidance-panel ul { margin: 18px 0 0; padding-left: 18px; color: #445249; font-size: 13px; line-height: 1.7; }
.guidance-panel li { margin: 8px 0; }

.report-shell { margin-top: 18px; }
.report-toolbar { display: flex; justify-content: space-between; align-items: flex-end; gap: 24px; margin-bottom: 20px; }
.toolbar-actions { flex-wrap: wrap; justify-content: flex-end; gap: 9px; }
.copy-status { color: var(--green); font-size: 11px; font-weight: 800; }
.run-id { margin: 9px 0 0; color: var(--muted); font-size: 12px; }
code { padding: 3px 5px; color: var(--green-dark); background: #e6eee8; font-size: 11px; }
.report-disclaimer { margin-bottom: 18px; border-left: 4px solid var(--orange); padding: 14px 16px; color: #604c3e; background: #fff4ec; font-size: 12px; line-height: 1.6; }
.model-review-card { margin-bottom: 18px; border: 1px solid #b8cdbb; padding: 22px; background: #edf5eb; }
.model-review-heading { display: flex; justify-content: space-between; align-items: flex-start; gap: 18px; }
.model-review-heading h3 { margin: 0; font-size: 18px; letter-spacing: -.03em; }
.model-confidence { padding: 6px 9px; color: var(--green); background: #d5e6d6; font-size: 10px; font-weight: 800; text-transform: uppercase; }
.model-assessment { max-width: 850px; margin: 18px 0; color: var(--ink) !important; font-size: 15px !important; }
.model-columns { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; border-top: 1px solid #c8d9c9; padding-top: 16px; }
.mini-label { margin: 0 0 10px !important; color: var(--green) !important; font-size: 10px !important; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; }
.report-overview { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.2fr); gap: 18px; margin-bottom: 18px; }
.report-card { min-width: 0; padding: 22px; }
.report-card h3 { margin: 0 0 15px; font-size: 15px; letter-spacing: -0.02em; }
.report-card p { color: #536057; font-size: 13px; line-height: 1.65; }
.impact-value { display: block; margin: 5px 0 12px; font-size: 30px; letter-spacing: -0.05em; text-transform: capitalize; }
.impact-positive { color: #1d8057; }
.impact-negative { color: #b84436; }
.impact-mixed { color: #bd711c; }
.impact-neutral { color: #69756c; }
.tag-list { display: flex; flex-wrap: wrap; gap: 7px; margin-top: 16px; }
.tag-list span, .count-badge { padding: 5px 8px; color: var(--green); background: #e7f0e9; font-size: 10px; font-weight: 700; }
.report-grid { display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(280px, .8fr); gap: 18px; }
.wide-card { grid-column: span 2; }
.section-heading { justify-content: space-between; gap: 14px; }
.risk-list { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }
.risk-card { border-left: 3px solid #ca8b28; padding: 14px; background: #fff9ec; }
.risk-card.severity-high { border-left-color: #b84436; background: #fff1ed; }
.risk-heading { justify-content: space-between; gap: 10px; color: #704a18; font-size: 12px; }
.severity-high .risk-heading { color: #8e2e25; }
.risk-heading span { font-size: 10px; text-transform: uppercase; }
.risk-card p { margin: 9px 0; font-size: 12px; }
.risk-card small, .persona-card small, .rewrite-card small { color: var(--muted); font-size: 11px; line-height: 1.5; }
blockquote { margin: 10px 0 0; border-left: 2px solid #dfcda8; padding-left: 8px; color: #705d45; font-size: 11px; line-height: 1.5; }
.plain-list, .recommendation-list { margin: 0 0 20px; padding-left: 18px; color: #4a584e; font-size: 13px; line-height: 1.65; }
.plain-list li, .recommendation-list li { margin: 7px 0; }
.persona-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 12px; }
.persona-card { border: 1px solid var(--line); padding: 14px; background: #fff; }
.persona-heading { justify-content: space-between; align-items: flex-start; gap: 12px; font-size: 12px; }
.persona-heading span { font-size: 10px; text-transform: capitalize; }
.persona-card p { margin: 9px 0; font-size: 12px; }
.reaction-text { color: var(--ink) !important; }
.rewrite-card { margin-bottom: 14px; border-left: 3px solid var(--green); padding: 11px 13px; background: #f0f6f1; }
.rewrite-card strong { color: var(--green-dark); font-size: 12px; }
.rewrite-card p { margin: 8px 0; color: var(--ink); font-size: 12px; }
.detail-card { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 24px; }
.detail-column { min-width: 0; }
.metadata-grid { display: grid; grid-template-columns: minmax(170px, .5fr) minmax(0, 1.5fr); margin: 0; color: #4f5d53; font-size: 12px; }
.metadata-grid dt, .metadata-grid dd { margin: 0; border-top: 1px solid var(--line); padding: 9px 0; }
.metadata-grid dt { color: var(--muted); text-transform: capitalize; }
.metadata-grid dd { overflow-wrap: anywhere; }

@media (max-width: 900px) {
  .miroind-page { padding: 22px 18px 60px; }
  .hero-card, .report-toolbar, .miroind-header { align-items: flex-start; flex-direction: column; }
  .principles { min-width: 0; }
  .workspace-grid, .report-overview, .report-grid { grid-template-columns: 1fr; }
  .wide-card { grid-column: auto; }
  .toolbar-actions { flex-wrap: wrap; }
}

@media (max-width: 620px) {
  .panel, .report-card, .hero-card { padding: 18px; }
  .two-up, .three-up, .detail-card { grid-template-columns: 1fr; }
  .field-grid label { margin-bottom: 15px; }
  .hero-card h2 { font-size: 33px; }
  .load-row { align-items: stretch; flex-direction: column; }
  .load-row .secondary-button { min-height: 40px; }
}
</style>

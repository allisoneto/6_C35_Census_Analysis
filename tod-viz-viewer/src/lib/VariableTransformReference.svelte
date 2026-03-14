<script lang="ts">
  import { onMount } from 'svelte'
  import { selection } from './store.js'
  import {
    getTransformDefinition,
    getProportionFormula,
    ACS_PROPORTION_FORMULAS,
    DECENNIAL_PROPORTION_GROUPS,
  } from './variableTransformDocs.js'
  import type { SelectionState } from './manifest.js'

  /** Whether the reference panel is expanded. */
  let expanded = $state(false)

  /** Whether to show full reference (all variables) or only the current selection. */
  let showAll = $state(false)

  /** Current selection from store (updated via subscription). */
  let sel = $state<SelectionState | null>(null)

  onMount(() => {
    return selection.subscribe((s) => {
      sel = s
    })
  })

  /** Relevant content for current selection: transform def and (if proportion) variable formula. */
  const transformDef = $derived(
    sel?.transform ? getTransformDefinition(sel.transform) : null
  )
  const proportionFormula = $derived(
    sel?.source && sel?.variable && sel?.transform === 'proportion'
      ? getProportionFormula(sel.source, sel.variable)
      : null
  )

  /** Whether we have a selection to show filtered content. */
  const hasSelection = $derived(Boolean(sel?.variable && sel?.transform))
</script>

<div class="reference-panel">
  <button
    type="button"
    class="toggle"
    onclick={() => (expanded = !expanded)}
    aria-expanded={expanded}
  >
    <span class="toggle-icon">{expanded ? '▼' : '▶'}</span>
    Variable & Transform Reference
    {#if hasSelection && !showAll}
      <span class="filter-badge">— {sel?.variableLabel ?? sel?.variable} ({sel?.transform})</span>
    {/if}
  </button>

  {#if expanded}
    <div class="content">
      {#if !hasSelection}
        <p class="intro">Select a variable and transform above to see how values are calculated.</p>
      {:else if !showAll}
        <!-- Filtered: only the selected transform and (if proportion) variable formula -->
        {#if transformDef}
          <section>
            <h3>Transform: {transformDef.label}</h3>
            <div class="transform-item">
              <p class="intro">
                <strong>Formula:</strong> <code>{transformDef.formula}</code>
              </p>
              <p class="intro">{transformDef.description}</p>
            </div>
          </section>
        {/if}
        {#if proportionFormula}
          <section>
            <h3>Proportion: {proportionFormula.variableLabel}</h3>
            <p class="intro">
              <code>{proportionFormula.formula}</code><br />
              <span class="denom-label">÷ {proportionFormula.denominatorLabel} ({proportionFormula.denominatorVar})</span>
            </p>
            <p class="intro">
              The value is divided by the denominator variable (same GEOID, same year).
            </p>
          </section>
        {/if}
        <p class="show-all">
          <button type="button" class="link-btn" onclick={() => (showAll = true)}>
            Show full reference (all variables and transforms)
          </button>
        </p>
      {:else}
        <!-- Full reference: all transforms and proportion formulas -->
        <section>
          <h3>Transform Types</h3>
          <p class="intro">
            Each variable can be displayed with different transforms. The denominator for
            <em>per_aland</em> is static (land area); for <em>per_population</em> and
            <em>proportion</em>, both numerator and denominator vary by year.
          </p>
          <dl class="transform-list">
            {#each ['raw', 'count', 'per_aland', 'per_population', 'proportion'] as id}
              {#if getTransformDefinition(id)}
                {@const t = getTransformDefinition(id)!}
                <div class="transform-item">
                  <dt>
                    <code>{t.id}</code> — {t.label}
                  </dt>
                  <dd>
                    <strong>Formula:</strong> <code>{t.formula}</code><br />
                    {t.description}
                  </dd>
                </div>
              {/if}
            {/each}
          </dl>
        </section>

        <section>
          <h3>ACS Proportion Formulas</h3>
          <p class="intro">
            For variables with the <em>proportion</em> transform, the value is divided by the
            denominator variable below (same GEOID, same year).
          </p>
          <table class="formula-table">
            <thead>
              <tr>
                <th>Variable</th>
                <th>Formula</th>
              </tr>
            </thead>
            <tbody>
              {#each ACS_PROPORTION_FORMULAS as f}
                <tr>
                  <td>
                    <code>{f.variable}</code><br />
                    <span class="var-label">{f.variableLabel}</span>
                  </td>
                  <td>
                    <code>{f.formula}</code><br />
                    <span class="denom-label">÷ {f.denominatorLabel} ({f.denominatorVar})</span>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </section>

        <section>
          <h3>Decennial Proportion Formulas</h3>
          <p class="intro">
            Grouped by denominator. Each variable in a group uses the same denominator.
          </p>
          {#each DECENNIAL_PROPORTION_GROUPS as group}
            <div class="decennial-group">
              <h4>÷ {group.denominatorLabel} (<code>{group.denominatorVar}</code>)</h4>
              <ul>
                {#each group.variables as v}
                  <li><code>{v.variable}</code> — {v.variableLabel}</li>
                {/each}
              </ul>
            </div>
          {/each}
        </section>

        {#if hasSelection}
          <p class="show-all">
            <button type="button" class="link-btn" onclick={() => (showAll = false)}>
              Show only current selection ({sel?.variableLabel ?? sel?.variable}, {sel?.transform})
            </button>
          </p>
        {/if}
      {/if}
    </div>
  {/if}
</div>

<style>
  /* Use theme-aware colors for readability on both light and dark backgrounds. */
  .reference-panel {
    margin-top: 1.5rem;
    border: 1px solid var(--border, #ddd);
    border-radius: 6px;
    overflow: hidden;
    background: var(--code-bg, #fafafa);
  }

  .toggle {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    width: 100%;
    padding: 0.6rem 1rem;
    font-size: 0.95rem;
    font-weight: 600;
    text-align: left;
    color: var(--text-h, #08060d);
    background: var(--border, #e5e4e7);
    border: none;
    cursor: pointer;
  }

  .toggle:hover {
    background: #d4d3d6;
  }

  @media (prefers-color-scheme: dark) {
    .toggle:hover {
      background: #3a3c45;
    }
  }

  .toggle-icon {
    font-size: 0.7rem;
    color: var(--text-h, #08060d);
  }

  .filter-badge {
    font-weight: 400;
    font-size: 0.85rem;
    color: var(--text, #555);
  }

  .link-btn {
    background: none;
    border: none;
    padding: 0;
    font-size: inherit;
    color: #4a90d9;
    cursor: pointer;
    text-decoration: underline;
  }

  .link-btn:hover {
    color: #2a70b9;
  }

  .content {
    padding: 1rem 1.25rem;
    max-height: 70vh;
    overflow-y: auto;
    color: var(--text-h, #08060d);
  }

  section {
    margin-bottom: 1.5rem;
  }

  section:last-child {
    margin-bottom: 0;
  }

  h3 {
    font-size: 1rem;
    margin: 0 0 0.5rem 0;
    color: var(--text-h, #08060d);
  }

  h4 {
    font-size: 0.9rem;
    margin: 0.75rem 0 0.35rem 0;
    color: var(--text-h, #08060d);
  }

  .intro {
    font-size: 0.85rem;
    color: var(--text, #333);
    margin: 0 0 0.75rem 0;
    line-height: 1.4;
  }

  .transform-list {
    margin: 0;
  }

  .transform-item {
    margin-bottom: 0.75rem;
  }

  .transform-item dt {
    font-weight: 600;
    font-size: 0.9rem;
    margin-bottom: 0.2rem;
    color: var(--text-h, #08060d);
  }

  .transform-item dd {
    margin: 0 0 0 1rem;
    font-size: 0.85rem;
    color: var(--text, #333);
    line-height: 1.4;
  }

  .formula-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.8rem;
  }

  .formula-table th,
  .formula-table td {
    padding: 0.4rem 0.6rem;
    text-align: left;
    border-bottom: 1px solid var(--border, #e0e0e0);
    vertical-align: top;
  }

  .formula-table th {
    background: var(--border, #eee);
    font-weight: 600;
    color: var(--text-h, #08060d);
  }

  .formula-table code {
    font-size: 0.85em;
    background: var(--code-bg, #e8e8e8);
    padding: 1px 4px;
    border-radius: 3px;
    color: var(--text-h, #08060d);
  }

  .var-label,
  .denom-label {
    font-size: 0.75rem;
    color: var(--text, #444);
  }

  .decennial-group {
    margin-bottom: 1rem;
  }

  .decennial-group ul {
    margin: 0.25rem 0 0 1rem;
    padding: 0;
    font-size: 0.8rem;
    line-height: 1.5;
  }

  .decennial-group li {
    margin-bottom: 0.2rem;
    color: var(--text-h, #08060d);
  }
</style>

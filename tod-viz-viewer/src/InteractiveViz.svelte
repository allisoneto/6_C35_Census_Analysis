<script lang="ts">
  import { onMount } from 'svelte'
  import { selection } from './lib/store.js'
  import { renderInteractiveVizApp, getInitialSelection } from './lib/d3/d3InteractiveApp.js'
  import NavBar from './lib/NavBar.svelte'
  import type { Manifest } from './lib/manifest.js'

  /** Mount point for D3. */
  let container = $state<HTMLDivElement | undefined>(undefined)

  /** Loaded manifest. */
  let manifest = $state<Manifest | null>(null)

  /** Load manifest and set initial selection (prefer choropleth for interactive page). */
  onMount(async () => {
    try {
      const res = await fetch('/manifest.json')
      manifest = await res.json()
      const initial = getInitialChoroplethSelection(manifest) ?? getInitialSelection(manifest)
      selection.set(initial)
    } catch (err) {
      console.error('Failed to load manifest:', err)
      manifest = {
        chartTypes: [],
        choropleth: { acs: { variables: [] }, decennial: { variables: [] } },
        pie_chart: { acs: { variables: [] }, decennial: { variables: [] } },
        bar_chart: { acs: { variables: [] }, decennial: { variables: [] } },
        stacked_bar: { acs: { variables: [] }, decennial: { variables: [] } },
        scatter: { acs: { variables: [] }, decennial: { variables: [] } },
      } as Manifest
      selection.set(null)
    }
  })

  /** Prefer choropleth as initial selection on interactive page. */
  function getInitialChoroplethSelection(m: Manifest): ReturnType<typeof getInitialSelection> {
    const chart = m.choropleth
    if (!chart) return null
    const source = chart.acs?.variables?.length ? 'acs' : 'decennial'
    const src = chart[source]
    const vars = src?.variables ?? []
    if (vars.length === 0) return null
    const v = vars[0]
    const years = v.years ?? []
    const year = years[0] ?? new Date().getFullYear()
    const transforms = v.transforms ?? ['default']
    const transform = transforms[0] ?? 'default'
    return {
      chartType: 'choropleth',
      source: source as 'acs' | 'decennial',
      variable: v.id,
      variableLabel: v.label,
      transform,
      extent: 'whole',
      acsGeography: 'unified_2010',
      mbtaOverlay: 'major',
      year,
      years,
      imagePath: '',
    }
  }

  /** Re-render when selection or manifest changes. */
  onMount(() => {
    const unsub = selection.subscribe((s) => {
      if (container && manifest) {
        renderInteractiveVizApp(container, manifest, s, (newS) => selection.set(newS))
      }
    })
    return () => unsub()
  })
</script>

<div class="app">
  <h1>TOD Census — Interactive D3 Viewer</h1>
  <NavBar currentPage="interactive" />
  <p class="subtitle">
    Choropleth maps with zoom, pan, and TOD project markers.<!-- Run
    <code>python tod-viz-viewer/scripts/export_d3_data.py</code> to generate variable data. -->
  </p>
  <div bind:this={container} class="viz-mount"></div>
</div>

<style>
  .app {
    font-family: system-ui, -apple-system, sans-serif;
    max-width: 1200px;
    margin: 0 auto;
    padding: 1rem;
  }
  h1 {
    font-size: 1.5rem;
    margin-bottom: 0.5rem;
  }
  .subtitle {
    font-size: 0.85rem;
    color: #666;
    margin-bottom: 1rem;
  }
  .subtitle code {
    background: #888;
    color: #fff;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 0.8rem;
  }
  .viz-mount {
    min-height: 200px;
  }
  :global(.controls) {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: center;
    gap: 5px;
    margin-bottom: 8px;
  }
  :global(.chart-select) {
    font-size: 8.5px;
    padding: 2px 5px;
    border-radius: 3px;
    border: 1px solid #ccc;
  }
  :global(.controls label) {
    font-size: 8.5px;
  }
  :global(.chart-view-container) {
    display: flex;
    justify-content: center;
    align-items: flex-start;
  }
  :global(.slider-container) {
    display: flex;
    justify-content: center;
  }
  :global(.chart-container) {
    display: flex;
    justify-content: center;
  }
  :global(.year-prev:hover),
  :global(.year-next:hover) {
    background: #c8c8c8 !important;
    border-color: #4a90d9 !important;
  }
  :global(.choropleth-svg) {
    max-width: 100%;
    height: auto;
  }
  :global(.time-series-panel) {
    min-height: 220px;
  }
</style>

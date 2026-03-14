<script lang="ts">
  import { onMount } from 'svelte'
  import { selection } from './lib/store.js'
  import { renderVizApp, getInitialSelection } from './lib/d3/d3App.js'
  import NavBar from './lib/NavBar.svelte'
  import type { Manifest } from './lib/manifest.js'

  /** Mount point for D3. */
  let container = $state<HTMLDivElement | undefined>(undefined)

  /** Loaded manifest. */
  let manifest = $state<Manifest | null>(null)

  /** Load manifest and set initial selection. */
  onMount(async () => {
    try {
      const res = await fetch('/manifest.json')
      manifest = await res.json()
      const initial = getInitialSelection(manifest)
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

  /** Re-render when selection or manifest changes. Use subscribe for reliable store updates. */
  onMount(() => {
    const unsub = selection.subscribe((s) => {
      if (container && manifest) {
        renderVizApp(container, manifest, s, (newS) => selection.set(newS))
      }
    })
    return () => unsub()
  })
</script>

<div class="app">
  <h1>TOD Census Visualization Viewer</h1>
  <NavBar currentPage="main" />
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
  :global(.chart-view-container img) {
    display: block;
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
</style>

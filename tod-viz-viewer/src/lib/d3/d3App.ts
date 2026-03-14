/**
 * Main D3 orchestration: renders full UI (dropdowns, slider, chart view).
 */

import * as d3 from 'd3'
import type { Manifest, SelectionState } from '../manifest.js'
import { renderDropdowns } from './d3Dropdowns.js'
import { renderYearSlider } from './d3YearSlider.js'
import { renderChartView } from './d3ChartView.js'
import { pngRenderer, getImagePath } from './renderers/pngRenderer.js'
import { preloadImages } from './preload.js'

/** Get default/initial selection from manifest. */
export function getInitialSelection(manifest: Manifest): SelectionState | null {
  const chartTypes = manifest.chartTypes
  if (chartTypes.length === 0) return null

  for (const chartType of chartTypes) {
    const chart = manifest[chartType as keyof Manifest] as
      | { acs: { variables: { id: string; label: string; transforms?: string[]; years: number[] }[] }; decennial: { variables: { id: string; label: string; transforms?: string[]; years: number[] }[] } }
      | undefined
    if (!chart) continue

    const source = chart.acs?.variables?.length ? 'acs' : 'decennial'
    const src = chart[source]
    const vars = src?.variables ?? []
    if (vars.length === 0) continue

    const v = vars[0]
    const years = v.years ?? []
    const year = years[0] ?? new Date().getFullYear()
    const transforms = v.transforms ?? ['default']
    const transform = transforms[0] ?? 'default'

    return {
      chartType,
      source,
      variable: v.id,
      variableLabel: v.label,
      transform,
      year,
      years,
      imagePath: '',
    }
  }
  return null
}

/** Resolve image path for selection (used by pngRenderer and preload). */
function resolveImagePath(selection: SelectionState, manifest: Manifest): string {
  return getImagePath(selection, manifest)
}

/** Main render function. */
export function renderVizApp(
  container: HTMLElement,
  manifest: Manifest,
  selection: SelectionState | null,
  onChange: (s: SelectionState) => void
): void {
  const root = d3.select(container)
  root.selectAll('*').remove()

  if (!selection) {
    root
      .append('div')
      .attr('class', 'empty-state')
      .style('padding', '2rem')
      .style('text-align', 'center')
      .style('color', '#666')
      .text('No visualization data. Run the Python visualization scripts first.')
    return
  }

  // Update imagePath in selection
  const fullSelection: SelectionState = {
    ...selection,
    imagePath: resolveImagePath(selection, manifest),
  }

  renderDropdowns(root, manifest, fullSelection, (partial) => {
    const next = { ...fullSelection, ...partial }
    next.imagePath = resolveImagePath(next, manifest)
    onChange(next)
  })

  root.append('div').attr('class', 'slider-container').style('margin', '16px 0')

  renderYearSlider(
    root.select('.slider-container'),
    fullSelection.years,
    fullSelection.year,
    (year) => {
      const next = { ...fullSelection, year }
      onChange(next)
    }
  )

  root.append('div').attr('class', 'chart-container').style('margin-top', '16px')

  const spec = pngRenderer(fullSelection, manifest)
  renderChartView(
    root.select('.chart-container'),
    spec,
    fullSelection.year,
    fullSelection
  )

  preloadImages(fullSelection, manifest, getImagePath)
}

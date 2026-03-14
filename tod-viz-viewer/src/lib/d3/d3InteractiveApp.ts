/**
 * Interactive D3 app: choropleth uses native D3 renderer (zoom, TOD markers, smooth year transitions).
 * Other chart types fall back to PNG.
 */

import * as d3 from 'd3'
import type { Manifest, SelectionState, VisualizationSpec } from '../manifest.js'
import { renderDropdowns } from './d3Dropdowns.js'
import { renderYearSlider } from './d3YearSlider.js'
import { renderChartView } from './d3ChartView.js'
import { getImagePath } from './renderers/pngRenderer.js'
import { preloadImages } from './preload.js'
import { renderChoropleth } from './renderers/d3ChoroplethRenderer.js'
import { getInitialSelection } from './d3App.js'

export { getInitialSelection }

/** Resolve image path for selection. */
function resolveImagePath(selection: SelectionState, manifest: Manifest): string {
  return getImagePath(selection, manifest)
}

/** Choropleth uses D3; others use PNG. */
function getSpec(selection: SelectionState, manifest: Manifest): VisualizationSpec {
  if (selection.chartType === 'choropleth') {
    return {
      type: 'd3',
      render: (container, sel) => renderChoropleth(container, sel),
    }
  }
  return { type: 'image', url: getImagePath(selection, manifest) }
}

/** Main render function for interactive page. */
export function renderInteractiveVizApp(
  container: HTMLElement,
  manifest: Manifest,
  selection: SelectionState | null,
  onChange: (s: SelectionState) => void
): void {
  const root = d3.select(container)

  if (!selection) {
    root.selectAll('*').remove()
    root
      .append('div')
      .attr('class', 'empty-state')
      .style('padding', '2rem')
      .style('text-align', 'center')
      .style('color', '#666')
      .text('No visualization data. Run the Python visualization scripts first.')
    return
  }

  const extent = selection.extent ?? 'whole'
  const acsGeography = selection.acsGeography ?? 'unified_2010'
  const mbtaOverlay = selection.mbtaOverlay ?? 'major'
  const chartKey = `${selection.chartType}:${selection.source}:${selection.variable}:${selection.transform}:${extent}:${acsGeography}:${mbtaOverlay}`
  const prevChartKey = root.attr('data-chart-key')
  const yearOnlyChange = prevChartKey === chartKey && !root.select('.chart-container').empty()
  if (!yearOnlyChange) {
    root.selectAll('*').remove()
  }
  root.attr('data-chart-key', chartKey)

  const fullSelection: SelectionState = {
    ...selection,
    imagePath: resolveImagePath(selection, manifest),
  }

  renderDropdowns(root, manifest, fullSelection, (partial) => {
    const next = { ...fullSelection, ...partial }
    next.imagePath = resolveImagePath(next, manifest)
    onChange(next)
  }, { showExtent: false, showGeography: true, showMbtaOverlay: true })

  root.selectAll('.slider-container').data([null]).join(
    (enter) =>
      enter.append('div').attr('class', 'slider-container').style('margin', '16px 0')
  )

  renderYearSlider(
    root.select('.slider-container'),
    fullSelection.years,
    fullSelection.year,
    (year) => {
      const next = { ...fullSelection, year }
      onChange(next)
    }
  )

  root.selectAll('.chart-container').data([null]).join(
    (enter) =>
      enter.append('div').attr('class', 'chart-container').style('margin-top', '16px')
  )

  const spec = getSpec(fullSelection, manifest)
  renderChartView(
    root.select('.chart-container'),
    spec,
    fullSelection.year,
    fullSelection,
    manifest,
    getImagePath
  )

  if (fullSelection.chartType !== 'choropleth') {
    preloadImages(fullSelection, manifest, getImagePath)
  }
}

/**
 * D3 chart view: displays either an image (PNG) or a D3-rendered chart.
 * For images: stacks all year images (preloaded) and shows only current - instant
 * switching with no black flash. Updates in place when only year changes.
 */

import * as d3 from 'd3'
import type { Manifest, SelectionState, VisualizationSpec } from '../manifest.js'

const TRANSITION_MS = 150
/** Image display size as fraction of container (80%). */
const IMAGE_SCALE = 0.6

type GetImagePath = (s: SelectionState, m: Manifest) => string

/** Render the chart area based on spec. */
export function renderChartView(
  root: d3.Selection<d3.BaseType, unknown, null, undefined>,
  spec: VisualizationSpec,
  year: number,
  selection: SelectionState,
  manifest: Manifest,
  getImagePath: GetImagePath
): void {
  // Stable key so container persists when only year changes (enables in-place update)
  const container = root
    .selectAll<HTMLDivElement, VisualizationSpec>('.chart-view-container')
    .data([spec], (d) => (d.type === 'image' ? 'image' : 'd3'))
    .join(
      (enter) =>
        enter
          .append('div')
          .attr('class', 'chart-view-container')
          .style('position', 'relative')
          .style('min-height', '400px'),
      (update) => update,
      (exit) => exit.remove()
    )

  container.each(function (d) {
    const sel = d3.select(this)

    if (d.type === 'image') {
      const wrapper = sel.select<HTMLDivElement>('.img-wrapper')
      const years = selection.years
      const wrapperExists = !wrapper.empty()

      // Rebuild if wrapper missing or years changed (e.g. different variable)
      const imgs = wrapper.selectAll('img.chart-img')
      const yearsMatch =
        wrapperExists &&
        years.length === imgs.size() &&
        years.every((y) => !wrapper.select(`img[data-year="${y}"]`).empty())

      if (!wrapperExists || !yearsMatch) {
        sel.selectAll('*').remove()
        const newWrapper = sel
          .append('div')
          .attr('class', 'img-wrapper')
          .style('position', 'relative')
          .style('max-width', `${IMAGE_SCALE * 100}%`)
          .style('margin', '0 auto')
          .style('display', 'block')

        years.forEach((y) => {
          const url = getImagePath({ ...selection, year: y }, manifest)
          const isCurrent = y === year
          newWrapper
            .append('img')
            .attr('class', 'chart-img')
            .attr('alt', `Census visualization ${y}`)
            .attr('src', url)
            .attr('data-year', String(y))
            .style('max-width', '100%')
            .style('height', 'auto')
            .style('position', isCurrent ? 'static' : 'absolute')
            .style('top', 0)
            .style('left', 0)
            .style('opacity', isCurrent ? 1 : 0)
            .style('pointer-events', isCurrent ? 'auto' : 'none')
            .on('error', function () {
              d3.select(this).style('display', 'none')
              if (y === year) {
                newWrapper
                  .append('div')
                  .attr('class', 'image-error')
                  .style('padding', '2rem')
                  .style('color', '#666')
                  .style('text-align', 'center')
                  .text('Image not found. Run the visualization scripts to generate.')
              }
            })
        })
      } else {
        // In-place update: just change which image is visible
        sel
          .select('.img-wrapper')
          .selectAll<HTMLImageElement, unknown>('img.chart-img')
          .each(function () {
            const img = d3.select(this)
            const imgYear = parseInt(img.attr('data-year') ?? '', 10)
            const isCurrent = imgYear === year
            img
              .transition()
              .duration(TRANSITION_MS)
              .style('opacity', isCurrent ? 1 : 0)
              .style('pointer-events', isCurrent ? 'auto' : 'none')
              .style('position', isCurrent ? 'static' : 'absolute')
          })
        sel.select('.image-error').remove()
      }
    } else if (d.type === 'd3') {
      // Stable inner div so D3 renderer can update in place on year change (no black flash)
      const inner = sel
        .selectAll<HTMLDivElement, null>('.d3-chart-inner')
        .data([null])
        .join(
          (enter) =>
            enter
              .append('div')
              .attr('class', 'd3-chart-inner')
              .style('width', '100%')
              .style('min-height', '400px'),
          (update) => update,
          (exit) => exit.remove()
        )
      if (inner.node()) {
        d.render(inner.node(), selection)
      }
    }
  })
}

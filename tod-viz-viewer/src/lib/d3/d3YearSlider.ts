/**
 * D3 year slider: discrete scale (snaps to each year), arrow buttons.
 */

import * as d3 from 'd3'
import { yearFormat } from './scales.js'

const SLIDER_WIDTH = 600
const SLIDER_HEIGHT = 60
const THUMB_R = 8

/** Render the year slider with left/right arrow buttons. Thumb snaps to discrete years. */
export function renderYearSlider(
  root: d3.Selection<d3.BaseType, unknown, null, undefined>,
  years: number[],
  selectedYear: number,
  onChange: (year: number) => void
): void {
  if (years.length === 0) return

  /** Get previous year in list, or current if at start. */
  const prevYear = () => {
    const i = years.indexOf(selectedYear)
    return i > 0 ? years[i - 1] : selectedYear
  }
  /** Get next year in list, or current if at end. */
  const nextYear = () => {
    const i = years.indexOf(selectedYear)
    return i >= 0 && i < years.length - 1 ? years[i + 1] : selectedYear
  }

  // Discrete scale: each year maps to a fixed position (snaps thumb to years)
  const scale = d3
    .scalePoint<number>()
    .domain(years)
    .range([THUMB_R, SLIDER_WIDTH - THUMB_R])
    .padding(0.5)

  /** Find nearest year for a pixel position. */
  const yearAtPos = (px: number) => {
    const val = scale.domain().reduce((a, b) =>
      Math.abs((scale(b) ?? 0) - px) < Math.abs((scale(a) ?? 0) - px) ? b : a
    )
    return val
  }

  root.selectAll('*').remove()

  // Flex row: [prev button] [slider] [next button]
  const row = root
    .append('div')
    .attr('class', 'year-slider-row')
    .style('display', 'flex')
    .style('align-items', 'center')
    .style('gap', '8px')

  // Left arrow button
  const prevBtn = row
    .append('button')
    .attr('class', 'year-prev')
    .attr('type', 'button')
    .attr('aria-label', 'Previous year')
    .style('width', '36px')
    .style('height', '36px')
    .style('padding', '0')
    .style('border', '1px solid #999')
    .style('border-radius', '4px')
    .style('background', '#e0e0e0')
    .style('color', '#333')
    .style('cursor', 'pointer')
    .style('font-size', '18px')
    .style('flex-shrink', '0')
    .text('‹')

  prevBtn.node()?.addEventListener('click', () => {
    const y = prevYear()
    if (y !== selectedYear) onChange(y)
  })

  // Slider SVG
  const svg = row
    .append('svg')
    .attr('class', 'year-slider')
    .attr('width', SLIDER_WIDTH)
    .attr('height', SLIDER_HEIGHT)

  const g = svg.append('g').attr('transform', `translate(0, ${THUMB_R})`)

  // Track line
  g.append('line')
    .attr('x1', THUMB_R)
    .attr('x2', SLIDER_WIDTH - THUMB_R)
    .attr('y1', 0)
    .attr('y2', 0)
    .attr('stroke', '#ccc')
    .attr('stroke-width', 2)

  // Axis
  const axis = d3
    .axisBottom(scale as d3.AxisScale<d3.NumberValue>)
    .tickFormat((d) => yearFormat(d as number))
    .tickSizeOuter(0)
    .tickSizeInner(4)

  g.append('g')
    .attr('transform', `translate(0, 20)`)
    .call(axis)
    .selectAll('text')
    .attr('font-size', '10px')

  // Clickable track
  g.append('rect')
    .attr('x', THUMB_R)
    .attr('y', -THUMB_R - 4)
    .attr('width', SLIDER_WIDTH - 2 * THUMB_R)
    .attr('height', THUMB_R * 2 + 8)
    .attr('fill', 'transparent')
    .style('cursor', 'pointer')
    .style('pointer-events', 'all')
    .on('click', function (event) {
      event.stopPropagation()
      const [px] = d3.pointer(event, svg.node())
      const nearest = yearAtPos(px)
      onChange(nearest)
    })

  // Thumb - snaps to discrete year positions
  const x = scale(selectedYear) ?? SLIDER_WIDTH / 2

  g
    .append('circle')
    .attr('class', 'year-thumb')
    .attr('cx', x)
    .attr('cy', 0)
    .attr('r', THUMB_R)
    .attr('fill', '#4a90d9')
    .attr('stroke', '#2a70b9')
    .attr('stroke-width', 2)
    .style('cursor', 'grab')
    .style('pointer-events', 'all')
    .call(
      d3
        .drag<SVGCircleElement, unknown>()
        .subject(function () {
          return { x: parseFloat(d3.select(this).attr('cx')), y: 0 }
        })
        .on('drag', function (event) {
          // Only update thumb position during drag; don't call onChange (avoids re-render mid-drag)
          const [px] = d3.pointer(event, svg.node())
          const nearest = yearAtPos(px)
          const newX = scale(nearest) ?? px
          d3.select(this).attr('cx', newX)
        })
        .on('end', function () {
          const cx = parseFloat(d3.select(this).attr('cx'))
          const nearest = yearAtPos(cx)
          const newX = scale(nearest) ?? cx
          d3.select(this).attr('cx', newX)
          onChange(nearest)
        })
    )

  // Right arrow button
  const nextBtn = row
    .append('button')
    .attr('class', 'year-next')
    .attr('type', 'button')
    .attr('aria-label', 'Next year')
    .style('width', '36px')
    .style('height', '36px')
    .style('padding', '0')
    .style('border', '1px solid #999')
    .style('border-radius', '4px')
    .style('background', '#e0e0e0')
    .style('color', '#333')
    .style('cursor', 'pointer')
    .style('font-size', '18px')
    .style('flex-shrink', '0')
    .text('›')

  nextBtn.node()?.addEventListener('click', () => {
    const y = nextYear()
    if (y !== selectedYear) onChange(y)
  })
}

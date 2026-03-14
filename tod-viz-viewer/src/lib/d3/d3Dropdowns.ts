/**
 * D3 dropdowns: chart type, source, variable, transform.
 * Uses data join for options.
 */

import * as d3 from 'd3'
import { transformLabelScale } from './scales.js'
import type { Manifest, SelectionState } from '../manifest.js'

const SOURCES = [
  { id: 'acs', label: 'ACS' },
  { id: 'decennial', label: 'Decennial' },
] as const

function getChartTypeData(manifest: Manifest) {
  return manifest.chartTypes.map((id) => ({
    id,
    label: id.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
  }))
}

function getVariableData(manifest: Manifest, chartType: string, source: string) {
  const chart = manifest[chartType as keyof Manifest]
  if (!chart || typeof chart !== 'object' || !('acs' in chart)) return []
  const sources = chart as { acs: { variables: { id: string; label: string }[] }; decennial: { variables: { id: string; label: string }[] } }
  const data = source === 'acs' ? sources.acs : sources.decennial
  return (data?.variables ?? []).map((v) => ({ id: v.id, label: v.label }))
}

function getTransformData(manifest: Manifest, chartType: string, source: string, variable: string) {
  const chart = manifest[chartType as keyof Manifest]
  if (!chart || typeof chart !== 'object' || !('acs' in chart)) return []
  const sources = chart as { acs: { variables: { id: string; transforms?: string[] }[] }; decennial: { variables: { id: string; transforms?: string[] }[] } }
  const data = source === 'acs' ? sources.acs : sources.decennial
  const v = data?.variables?.find((x) => x.id === variable)
  const transforms = v?.transforms ?? ['default']
  return transforms.map((t) => ({ id: t, label: transformLabelScale(t) ?? t }))
}

/** Render all dropdowns. */
export function renderDropdowns(
  root: d3.Selection<d3.BaseType, unknown, null, undefined>,
  manifest: Manifest,
  selection: SelectionState,
  onChange: (s: Partial<SelectionState>) => void
): void {
  const controls = root
    .selectAll<HTMLDivElement, unknown>('.controls')
    .data([null])
    .join((enter) => enter.append('div').attr('class', 'controls'))

  const chartTypes = getChartTypeData(manifest)
  const variables = getVariableData(manifest, selection.chartType, selection.source)
  const transforms = getTransformData(manifest, selection.chartType, selection.source, selection.variable)

  // Chart type
  renderSelect(controls, 'chart-type', 'Chart Type', chartTypes, selection.chartType, (id) => {
    const chart = manifest[id as keyof Manifest] as { acs: { variables: { id: string; label: string; transforms?: string[]; years: number[] }[] }; decennial: { variables: { id: string; label: string; transforms?: string[]; years: number[] }[] } } | undefined
    if (!chart) return
    const src = chart[selection.source as 'acs' | 'decennial']
    const vars = src?.variables ?? []
    const first = vars[0]
    const years = first?.years ?? []
    const firstYear = years[0] ?? new Date().getFullYear()
    const transforms = first?.transforms ?? ['default']
    onChange({
      chartType: id,
      variable: first?.id ?? '',
      variableLabel: first?.label ?? '',
      transform: transforms[0] ?? 'default',
      year: firstYear,
      years,
    })
  })

  // Source
  renderSelect(controls, 'source', 'Data Source', SOURCES, selection.source, (id) => {
    const chart = manifest[selection.chartType as keyof Manifest] as { acs: { variables: { id: string; label: string; transforms?: string[]; years: number[] }[] }; decennial: { variables: { id: string; label: string; transforms?: string[]; years: number[] }[] } } | undefined
    if (!chart) return
    const src = chart[id as 'acs' | 'decennial']
    const vars = src?.variables ?? []
    const first = vars[0]
    const years = first?.years ?? []
    const firstYear = years[0] ?? new Date().getFullYear()
    const transforms = first?.transforms ?? ['default']
    onChange({
      source: id as 'acs' | 'decennial',
      variable: first?.id ?? '',
      variableLabel: first?.label ?? '',
      transform: transforms[0] ?? 'default',
      year: firstYear,
      years,
    })
  })

  // Variable
  renderSelect(controls, 'variable', 'Variable', variables, selection.variable, (id) => {
    const v = variables.find((x) => x.id === id)
    if (!v) return
    const chart = manifest[selection.chartType as keyof Manifest] as { acs: { variables: { id: string; label: string; transforms?: string[]; years: number[] }[] }; decennial: { variables: { id: string; label: string; transforms?: string[]; years: number[] }[] } } | undefined
    if (!chart) return
    const src = chart[selection.source as 'acs' | 'decennial']
    const vars = src?.variables ?? []
    const vv = vars.find((x) => x.id === id)
    const years = vv?.years ?? []
    const firstYear = years[0] ?? new Date().getFullYear()
    const transforms = vv?.transforms ?? ['default']
    onChange({
      variable: id,
      variableLabel: v.label,
      transform: transforms[0] ?? 'default',
      year: firstYear,
      years,
    })
  })

  // Transform (only if multiple)
  const transformContainer = controls
    .selectAll<HTMLDivElement, boolean>('.transform-container')
    .data([transforms.length > 1])
    .join(
      (enter) =>
        enter
          .append('div')
          .attr('class', 'transform-container')
          .style('display', (d) => (d ? 'block' : 'none')),
      (update) => update.style('display', (d) => (d ? 'block' : 'none')),
      (exit) => exit.remove()
    )

  transformContainer.each(function (show) {
    if (show) {
      renderSelect(
        d3.select(this),
        'transform',
        'Transform',
        transforms,
        selection.transform,
        (id) => onChange({ transform: id })
      )
    }
  })
}

function renderSelect(
  parent: d3.Selection<d3.BaseType, unknown, null, undefined>,
  id: string,
  label: string,
  options: { id: string; label: string }[],
  value: string,
  onChange: (id: string) => void
): void {
  const wrap = parent
    .selectAll<HTMLDivElement, string>(`div.${id}-wrap`)
    .data([id])
    .join(
      (enter) =>
        enter
          .append('div')
          .attr('class', `${id}-wrap`)
          .style('display', 'inline-block')
          .style('margin-right', '12px')
          .style('margin-bottom', '8px'),
      (update) => update,
      (exit) => exit.remove()
    )

  wrap.selectAll('label').data([label]).join('label').text((d) => d).attr('for', `${id}-select`)

  const select = wrap
    .selectAll<HTMLSelectElement, string[]>(`select#${id}-select`)
    .data([options])
    .join(
      (enter) =>
        enter
          .append('select')
          .attr('id', `${id}-select`)
          .attr('class', 'chart-select')
          .style('margin-left', '4px')
          .style('padding', '4px 8px')
          .on('change', function () {
            const id = (this as HTMLSelectElement).value
            onChange(id)
          }),
      (update) => update,
      (exit) => exit.remove()
    )

  const opts = select
    .selectAll<HTMLOptionElement, { id: string; label: string }>('option')
    .data(options, (d) => d.id)
    .join(
      (enter) =>
        enter
          .append('option')
          .attr('value', (d) => d.id)
          .text((d) => d.label),
      (update) => update.text((d) => d.label),
      (exit) => exit.remove()
    )

  select.property('value', value)
}

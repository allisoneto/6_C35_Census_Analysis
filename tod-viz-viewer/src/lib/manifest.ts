/**
 * Types for the census visualization manifest and selection state.
 */

export interface ManifestVariable {
  id: string
  label: string
  transforms?: string[]
  years: number[]
}

export interface ManifestSourceData {
  variables: ManifestVariable[]
}

export interface ManifestChartType {
  acs: ManifestSourceData
  decennial: ManifestSourceData
}

export interface Manifest {
  chartTypes: string[]
  choropleth: ManifestChartType
  pie_chart: ManifestChartType
  bar_chart: ManifestChartType
  stacked_bar: ManifestChartType
  scatter: ManifestChartType
}

/** Selection state passed to D3 and renderers. */
export interface SelectionState {
  chartType: string
  source: 'acs' | 'decennial'
  variable: string
  variableLabel: string
  transform: string
  year: number
  years: number[]
  imagePath: string
}

/** Unified spec for chart display: either image URL or D3 render function. */
export type VisualizationSpec =
  | { type: 'image'; url: string }
  | { type: 'd3'; render: (container: HTMLElement, selection: SelectionState) => void }

/** Renderer: (selection, manifest) => VisualizationSpec */
export type Renderer = (
  selection: SelectionState,
  manifest: Manifest
) => VisualizationSpec

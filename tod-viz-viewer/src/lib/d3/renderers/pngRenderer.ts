/**
 * PNG renderer: resolves image path from selection and manifest.
 * Returns { type: 'image', url } for the chart view to display.
 */

import type { Manifest, ManifestVariable, SelectionState, VisualizationSpec } from '../../manifest.js'

const BASE = '/output'

function humanReadableDirName(name: string): string {
  return name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()).replace(/ /g, '_')
}

/** Resolve image path for the current selection. */
export function getImagePath(
  selection: SelectionState,
  manifest: Manifest
): string {
  const { chartType, source, variable, variableLabel, transform, year } = selection

  switch (chartType) {
    case 'choropleth': {
      const humanName = humanReadableDirName(variableLabel)
      // Boston zoom PNGs live in boston_zoom subfolder; whole area at transform level
      const extent = selection.extent ?? 'whole'
      const extentDir = extent === 'boston' ? 'boston_zoom/' : ''
      return `${BASE}/maps/${source}/${humanName}/${transform}/${extentDir}${source}_${variable}_${transform}_${year}.png`
    }
    case 'pie_chart': {
      const group = variable
      const humanGroup = humanReadableDirName(variableLabel)
      return `${BASE}/pie_charts/${source}/${humanGroup}/${group}_agg_5geoids_${year}.png`
    }
    case 'bar_chart': {
      return `${BASE}/bar_charts/${source}/${variable}_n5geoids_${year}.png`
    }
    case 'stacked_bar': {
      const humanGroup = humanReadableDirName(variableLabel)
      return `${BASE}/stacked_bar_charts/${source}/${humanGroup}/${variable}_n5geoids_${year}.png`
    }
    case 'scatter': {
      const humanName = humanReadableDirName(variableLabel)
      return `${BASE}/scatter_plots/${source}/${humanName}/${transform}/overlap_total_vs_${variable}_${year}.png`
    }
    default:
      return ''
  }
}

/** PNG renderer: returns image spec from selection. */
export function pngRenderer(
  selection: SelectionState,
  manifest: Manifest
): VisualizationSpec {
  const url = getImagePath(selection, manifest)
  return { type: 'image', url }
}

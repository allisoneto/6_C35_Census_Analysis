/**
 * D3 scales and formatters for the viewer.
 */

import * as d3 from 'd3'

/** Map transform IDs to human-readable labels. */
export const transformLabelScale = d3
  .scaleOrdinal<string, string>()
  .domain(['count', 'proportion', 'raw', 'per_aland', 'per_population', 'default'])
  .range(['Count', 'Proportion', 'Raw', 'Per sq m', 'Per capita', 'Default'])

/** Format year for display. */
export const yearFormat = d3.format('d')

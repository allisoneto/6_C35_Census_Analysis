/**
 * Variable and transform documentation for the TOD Census viewer.
 * Explains what each transform does and how proportion denominators are defined.
 * Data derived from acs_variable_mapping.csv and decennial_variable_mapping_nhgis.csv.
 */

/** Transform type definition. */
export interface TransformDef {
  id: string
  label: string
  formula: string
  description: string
}

/** Proportion formula for a variable. */
export interface ProportionFormula {
  variable: string
  variableLabel: string
  formula: string
  denominatorVar: string
  denominatorLabel: string
}

/** Transform type definitions (what each transform does). */
export const TRANSFORM_DEFINITIONS: TransformDef[] = [
  {
    id: 'raw',
    label: 'Raw',
    formula: 'value',
    description: 'The raw census value with no transformation (e.g., median age, median income).',
  },
  {
    id: 'count',
    label: 'Count',
    formula: 'value',
    description: 'Same as raw—the count or value as reported by the Census.',
  },
  {
    id: 'per_aland',
    label: 'Per sq m',
    formula: 'value / land_area',
    description:
      'Value divided by land area (sq m). Land area is static per block group (same across years). Use for density (e.g., population per sq m).',
  },
  {
    id: 'per_population',
    label: 'Per capita',
    formula: 'value / population',
    description:
      'Value divided by total population (B01001_001E for ACS, CL8AA for decennial). Both numerator and denominator vary by year.',
  },
  {
    id: 'proportion',
    label: 'Proportion',
    formula: 'value / denominator',
    description:
      'Value divided by a variable-specific denominator (e.g., total housing units, total workers). Denominator is defined per variable below.',
  },
]

/** ACS proportion formulas (variable → denominator). */
export const ACS_PROPORTION_FORMULAS: ProportionFormula[] = [
  { variable: 'B17001_002E', variableLabel: 'Income below poverty (count)', formula: 'B17001_002E / B17001_001E', denominatorVar: 'B17001_001E', denominatorLabel: 'Population for poverty denominator' },
  { variable: 'B25003_002E', variableLabel: 'Owner-occupied units', formula: 'B25003_002E / B25001_001E', denominatorVar: 'B25001_001E', denominatorLabel: 'Total housing units' },
  { variable: 'B25003_003E', variableLabel: 'Renter-occupied units', formula: 'B25003_003E / B25001_001E', denominatorVar: 'B25001_001E', denominatorLabel: 'Total housing units' },
  { variable: 'B23025_002E', variableLabel: 'In labor force', formula: 'B23025_002E / B01001_001E', denominatorVar: 'B01001_001E', denominatorLabel: 'Total population' },
  { variable: 'B23025_005E', variableLabel: 'Employed', formula: 'B23025_005E / B23025_002E', denominatorVar: 'B23025_002E', denominatorLabel: 'In labor force' },
  { variable: 'B08301_003E', variableLabel: 'Drove alone', formula: 'B08301_003E / B08301_001E', denominatorVar: 'B08301_001E', denominatorLabel: 'Total workers (commuters)' },
  { variable: 'B08301_010E', variableLabel: 'Public transit', formula: 'B08301_010E / B08301_001E', denominatorVar: 'B08301_001E', denominatorLabel: 'Total workers (commuters)' },
  { variable: 'B08301_017E', variableLabel: 'Bicycle', formula: 'B08301_017E / B08301_001E', denominatorVar: 'B08301_001E', denominatorLabel: 'Total workers (commuters)' },
  { variable: 'B08301_018E', variableLabel: 'Walked', formula: 'B08301_018E / B08301_001E', denominatorVar: 'B08301_001E', denominatorLabel: 'Total workers (commuters)' },
  { variable: 'B08301_019E', variableLabel: 'Worked from home', formula: 'B08301_019E / B08301_001E', denominatorVar: 'B08301_001E', denominatorLabel: 'Total workers (commuters)' },
  { variable: 'B25044_003E', variableLabel: 'Owner-occupied units with no vehicle', formula: 'B25044_003E / B25044_002E', denominatorVar: 'B25044_002E', denominatorLabel: 'Owner-occupied units' },
  { variable: 'B25044_010E', variableLabel: 'Renter-occupied units with no vehicle', formula: 'B25044_010E / B25044_009E', denominatorVar: 'B25044_009E', denominatorLabel: 'Renter-occupied units' },
  { variable: 'B25044_004E', variableLabel: 'Owner-occupied units with 1 vehicle', formula: 'B25044_004E / B25044_002E', denominatorVar: 'B25044_002E', denominatorLabel: 'Owner-occupied units' },
  { variable: 'B25044_011E', variableLabel: 'Renter-occupied units with 1 vehicle', formula: 'B25044_011E / B25044_009E', denominatorVar: 'B25044_009E', denominatorLabel: 'Renter-occupied units' },
  { variable: 'B25002_002E', variableLabel: 'Occupied units', formula: 'B25002_002E / B25002_001E', denominatorVar: 'B25002_001E', denominatorLabel: 'Total housing units' },
  { variable: 'B25002_003E', variableLabel: 'Vacant units', formula: 'B25002_003E / B25002_001E', denominatorVar: 'B25002_001E', denominatorLabel: 'Total housing units' },
]

/** Decennial proportion formulas, grouped by denominator for readability. */
export interface DecennialProportionGroup {
  denominatorVar: string
  denominatorLabel: string
  variables: { variable: string; variableLabel: string }[]
}

export const DECENNIAL_PROPORTION_GROUPS: DecennialProportionGroup[] = [
  {
    denominatorVar: 'CM5AA',
    denominatorLabel: 'Total families',
    variables: [
      { variable: 'CS5AA', variableLabel: 'Families: Married-couple family' },
      { variable: 'CS5AB', variableLabel: '… With own children under 6 only' },
      { variable: 'CS5AC', variableLabel: '… Under 6 and 6–17' },
      { variable: 'CS5AD', variableLabel: '… 6–17 only' },
      { variable: 'CS5AE', variableLabel: '… No own children under 18' },
      { variable: 'CS5AF', variableLabel: 'Families: Male householder, no spouse' },
      { variable: 'CS5AG', variableLabel: '… With own children under 6 only' },
      { variable: 'CS5AH', variableLabel: '… Under 6 and 6–17' },
      { variable: 'CS5AI', variableLabel: '… 6–17 only' },
      { variable: 'CS5AJ', variableLabel: '… No own children under 18' },
      { variable: 'CS5AK', variableLabel: 'Families: Female householder, no spouse' },
      { variable: 'CS5AL', variableLabel: '… With own children under 6 only' },
      { variable: 'CS5AM', variableLabel: '… Under 6 and 6–17' },
      { variable: 'CS5AN', variableLabel: '… 6–17 only' },
      { variable: 'CS5AO', variableLabel: '… No own children under 18' },
    ],
  },
  {
    denominatorVar: 'CM4AA',
    denominatorLabel: 'Total households',
    variables: [
      { variable: 'CS2AA', variableLabel: 'Households: Family, 2 persons' },
      { variable: 'CS2AB', variableLabel: '… 3 persons' },
      { variable: 'CS2AC', variableLabel: '… 4 persons' },
      { variable: 'CS2AD', variableLabel: '… 5 persons' },
      { variable: 'CS2AE', variableLabel: '… 6 persons' },
      { variable: 'CS2AF', variableLabel: '… 7+ persons' },
      { variable: 'CS2AG', variableLabel: 'Households: Nonfamily, 1 person' },
      { variable: 'CS2AH', variableLabel: '… 2 persons' },
      { variable: 'CS2AI', variableLabel: '… 3 persons' },
      { variable: 'CS2AJ', variableLabel: '… 4 persons' },
      { variable: 'CS2AK', variableLabel: '… 5 persons' },
      { variable: 'CS2AL', variableLabel: '… 6 persons' },
      { variable: 'CS2AM', variableLabel: '… 7+ persons' },
      { variable: 'CS1AA', variableLabel: 'Households: Family' },
      { variable: 'CS1AB', variableLabel: '… Married-couple family' },
      { variable: 'CS1AC', variableLabel: '… Other family' },
      { variable: 'CS1AD', variableLabel: '… Male householder, no spouse' },
      { variable: 'CS1AE', variableLabel: '… Female householder, no spouse' },
      { variable: 'CS1AF', variableLabel: 'Households: Nonfamily' },
    ],
  },
  {
    denominatorVar: 'CS1AF',
    denominatorLabel: 'Nonfamily households',
    variables: [
      { variable: 'CS4AA', variableLabel: 'Nonfamily: 1 person (living alone)' },
      { variable: 'CS4AB', variableLabel: 'Nonfamily: 2+ persons' },
    ],
  },
  {
    denominatorVar: 'CM7AA',
    denominatorLabel: 'Total housing units',
    variables: [
      { variable: 'CM9AA', variableLabel: 'Housing units: Occupied' },
      { variable: 'CM9AB', variableLabel: 'Housing units: Vacant' },
    ],
  },
  {
    denominatorVar: 'CM9AA',
    denominatorLabel: 'Occupied housing units',
    variables: [
      { variable: 'CV8AA', variableLabel: 'Occupied: 1-person household' },
      { variable: 'CV8AB', variableLabel: '… 2-person' },
      { variable: 'CV8AC', variableLabel: '… 3-person' },
      { variable: 'CV8AD', variableLabel: '… 4-person' },
      { variable: 'CV8AE', variableLabel: '… 5-person' },
      { variable: 'CV8AF', variableLabel: '… 6-person' },
      { variable: 'CV8AG', variableLabel: '… 7+ person' },
      { variable: 'CY4AA', variableLabel: 'Occupied: Householder White' },
      { variable: 'CY4AB', variableLabel: '… Black or African American' },
      { variable: 'CY4AC', variableLabel: '… American Indian / Alaska Native' },
      { variable: 'CY4AD', variableLabel: '… Asian and Pacific Islander' },
      { variable: 'CY4AE', variableLabel: '… Some Other Race' },
      { variable: 'CY4AF', variableLabel: '… Two or More Races' },
      { variable: 'CN1AA', variableLabel: 'Owner-occupied units' },
      { variable: 'CN1AB', variableLabel: 'Renter-occupied units' },
      { variable: 'CV9AA', variableLabel: 'Owner: 1-person household' },
      { variable: 'CV9AB', variableLabel: 'Owner: 2-person' },
      { variable: 'CV9AC', variableLabel: 'Owner: 3-person' },
      { variable: 'CV9AD', variableLabel: 'Owner: 4-person' },
      { variable: 'CV9AE', variableLabel: 'Owner: 5-person' },
      { variable: 'CV9AF', variableLabel: 'Owner: 6-person' },
      { variable: 'CV9AG', variableLabel: 'Owner: 7+ person' },
      { variable: 'CV9AH', variableLabel: 'Renter: 1-person household' },
      { variable: 'CV9AI', variableLabel: 'Renter: 2-person' },
      { variable: 'CV9AJ', variableLabel: 'Renter: 3-person' },
      { variable: 'CV9AK', variableLabel: 'Renter: 4-person' },
      { variable: 'CV9AL', variableLabel: 'Renter: 5-person' },
      { variable: 'CV9AM', variableLabel: 'Renter: 6-person' },
      { variable: 'CV9AN', variableLabel: 'Renter: 7+ person' },
      { variable: 'CY5AA', variableLabel: 'Owner: Householder White' },
      { variable: 'CY5AB', variableLabel: 'Owner: Black or African American' },
      { variable: 'CY5AC', variableLabel: 'Owner: American Indian / Alaska Native' },
      { variable: 'CY5AD', variableLabel: 'Owner: Asian and Pacific Islander' },
      { variable: 'CY5AE', variableLabel: 'Owner: Some Other Race' },
      { variable: 'CY5AF', variableLabel: 'Owner: Two or More Races' },
      { variable: 'CY5AG', variableLabel: 'Renter: Householder White' },
      { variable: 'CY5AH', variableLabel: 'Renter: Black or African American' },
      { variable: 'CY5AI', variableLabel: 'Renter: American Indian / Alaska Native' },
      { variable: 'CY5AJ', variableLabel: 'Renter: Asian and Pacific Islander' },
      { variable: 'CY5AK', variableLabel: 'Renter: Some Other Race' },
      { variable: 'CY5AL', variableLabel: 'Renter: Two or More Races' },
    ],
  },
  {
    denominatorVar: 'CL8AA',
    denominatorLabel: 'Total population',
    variables: [
      { variable: 'CW3AA', variableLabel: 'Persons: Under 5 years' },
      { variable: 'CW3AB', variableLabel: '… 5 to 9 years' },
      { variable: 'CW3AC', variableLabel: '… 10 to 14 years' },
      { variable: 'CW3AD', variableLabel: '… 15 to 17 years' },
      { variable: 'CW3AE', variableLabel: '… 18 and 19 years' },
      { variable: 'CW3AF', variableLabel: '… 20 years' },
      { variable: 'CW3AG', variableLabel: '… 21 years' },
      { variable: 'CW3AH', variableLabel: '… 22 to 24 years' },
      { variable: 'CW3AI', variableLabel: '… 25 to 29 years' },
      { variable: 'CW3AJ', variableLabel: '… 30 to 34 years' },
      { variable: 'CW3AK', variableLabel: '… 35 to 39 years' },
      { variable: 'CW3AL', variableLabel: '… 40 to 44 years' },
      { variable: 'CW3AM', variableLabel: '… 45 to 49 years' },
      { variable: 'CW3AN', variableLabel: '… 50 to 54 years' },
      { variable: 'CW3AO', variableLabel: '… 55 to 59 years' },
      { variable: 'CW3AP', variableLabel: '… 60 and 61 years' },
      { variable: 'CW3AQ', variableLabel: '… 62 to 64 years' },
      { variable: 'CW3AR', variableLabel: '… 65 to 69 years' },
      { variable: 'CW3AS', variableLabel: '… 70 to 74 years' },
      { variable: 'CW3AT', variableLabel: '… 75 to 79 years' },
      { variable: 'CW3AU', variableLabel: '… 80 to 84 years' },
      { variable: 'CW3AV', variableLabel: '… 85 years and over' },
      { variable: 'CW7AA', variableLabel: 'Not Hispanic: White' },
      { variable: 'CW7AB', variableLabel: 'Not Hispanic: Black or African American' },
      { variable: 'CW7AC', variableLabel: 'Not Hispanic: American Indian / Alaska Native' },
      { variable: 'CW7AD', variableLabel: 'Not Hispanic: Asian and Pacific Islander' },
      { variable: 'CW7AE', variableLabel: 'Not Hispanic: Some Other Race' },
      { variable: 'CW7AF', variableLabel: 'Not Hispanic: Two or More Races' },
      { variable: 'CW7AG', variableLabel: 'Hispanic: White' },
      { variable: 'CW7AH', variableLabel: 'Hispanic: Black or African American' },
      { variable: 'CW7AI', variableLabel: 'Hispanic: American Indian / Alaska Native' },
      { variable: 'CW7AJ', variableLabel: 'Hispanic: Asian and Pacific Islander' },
      { variable: 'CW7AK', variableLabel: 'Hispanic: Some Other Race' },
      { variable: 'CW7AL', variableLabel: 'Hispanic: Two or More Races' },
      { variable: 'CM1AA', variableLabel: 'Persons: White (single race)' },
      { variable: 'CM1AB', variableLabel: '… Black or African American' },
      { variable: 'CM1AC', variableLabel: '… American Indian and Alaska Native' },
      { variable: 'CM1AD', variableLabel: '… Asian' },
      { variable: 'CM1AE', variableLabel: '… Native Hawaiian and Pacific Islander' },
      { variable: 'CM1AF', variableLabel: '… Some Other Race' },
      { variable: 'CM1AG', variableLabel: '… Two or More Races' },
      { variable: 'CY8AA', variableLabel: 'Not Hispanic: White (single race/ethnicity)' },
      { variable: 'CY8AB', variableLabel: 'Not Hispanic: Black or African American' },
      { variable: 'CY8AC', variableLabel: 'Not Hispanic: American Indian / Alaska Native' },
      { variable: 'CY8AD', variableLabel: 'Not Hispanic: Asian and Pacific Islander' },
      { variable: 'CY8AE', variableLabel: 'Not Hispanic: Some Other Race' },
      { variable: 'CY8AF', variableLabel: 'Hispanic or Latino' },
    ],
  },
  {
    denominatorVar: 'CP9AB',
    denominatorLabel: 'Persons in group quarters',
    variables: [
      { variable: 'CQ2AA', variableLabel: 'Group quarters: Correctional facilities' },
      { variable: 'CQ2AB', variableLabel: '… Nursing facilities' },
      { variable: 'CQ2AC', variableLabel: '… Other institutional' },
      { variable: 'CQ2AD', variableLabel: '… College/university student housing' },
      { variable: 'CQ2AE', variableLabel: '… Military quarters' },
      { variable: 'CQ2AF', variableLabel: '… Other noninstitutional' },
      { variable: 'CQ1AA', variableLabel: 'Group quarters: Institutionalized' },
      { variable: 'CQ1AB', variableLabel: 'Group quarters: Noninstitutionalized' },
    ],
  },
  {
    denominatorVar: 'CP9AA',
    denominatorLabel: 'Persons in households',
    variables: [
      { variable: 'CQ0AA', variableLabel: 'In family households' },
      { variable: 'CQ0AB', variableLabel: 'In nonfamily households' },
      { variable: 'D20AA', variableLabel: 'In family: Householder' },
      { variable: 'D20AB', variableLabel: '… Spouse' },
      { variable: 'D20AC', variableLabel: '… Biological or adopted child' },
      { variable: 'D20AD', variableLabel: '… Stepchild' },
      { variable: 'D20AE', variableLabel: '… Grandchild' },
      { variable: 'D20AF', variableLabel: '… Brother or sister' },
      { variable: 'D20AG', variableLabel: '… Parent' },
      { variable: 'D20AH', variableLabel: '… Other relatives' },
      { variable: 'D20AI', variableLabel: 'In nonfamily: Householder' },
      { variable: 'D20AJ', variableLabel: '… Nonrelatives' },
    ],
  },
  {
    denominatorVar: 'CM9AB',
    denominatorLabel: 'Vacant housing units',
    variables: [
      { variable: 'CN0AA', variableLabel: 'Vacant: For rent' },
      { variable: 'CN0AB', variableLabel: '… For sale only' },
      { variable: 'CN0AC', variableLabel: '… Rented or sold, not occupied' },
      { variable: 'CN0AD', variableLabel: '… Seasonal, recreational, or occasional' },
      { variable: 'CN0AE', variableLabel: '… For migrant workers' },
      { variable: 'CN0AF', variableLabel: '… Other vacant' },
    ],
  },
]

/** Flatten decennial groups into a lookup map: variable id → ProportionFormula. */
const DECENNIAL_PROPORTION_MAP = new Map<string, ProportionFormula>()
for (const group of DECENNIAL_PROPORTION_GROUPS) {
  for (const v of group.variables) {
    DECENNIAL_PROPORTION_MAP.set(v.variable, {
      variable: v.variable,
      variableLabel: v.variableLabel,
      formula: `${v.variable} / ${group.denominatorVar}`,
      denominatorVar: group.denominatorVar,
      denominatorLabel: group.denominatorLabel,
    })
  }
}

/**
 * Get the proportion formula for a variable, if it has one.
 *
 * Parameters
 * ----------
 * source : string
 *     Data source: 'acs', 'decennial', or 'decennial_extras'.
 * variable : string
 *     Census variable code (e.g., B25002_003E, CN0AA).
 *
 * Returns
 * -------
 * ProportionFormula | null
 *     The formula for that variable, or null if not a proportion variable.
 */
export function getProportionFormula(
  source: string,
  variable: string
): ProportionFormula | null {
  if (source === 'acs') {
    return ACS_PROPORTION_FORMULAS.find((f) => f.variable === variable) ?? null
  }
  if (source === 'decennial' || source === 'decennial_extras') {
    return DECENNIAL_PROPORTION_MAP.get(variable) ?? null
  }
  return null
}

/**
 * Get the transform definition for a transform id.
 */
export function getTransformDefinition(transform: string): TransformDef | null {
  const norm = transform === 'default' ? 'count' : transform
  return TRANSFORM_DEFINITIONS.find((t) => t.id === norm) ?? null
}

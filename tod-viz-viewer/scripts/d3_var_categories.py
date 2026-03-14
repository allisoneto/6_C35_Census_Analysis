"""
Hardcoded variable categories for D3 export and manifest.

Variables in the approved list go to the main source (decennial).
Variables NOT in the list go to the extras category (decennial_extras).
Values are from visualization/var_list.yaml; hardcoded here so export does not depend on YAML.

ACS_CHORO_VARS is "all" in var_list, so all ACS variables go to "acs" (no extras).
"""

# Choropleth variables from var_list.yaml DECENNIAL_CHORO_VARS
DECENNIAL_CHORO_APPROVED = frozenset({
    "CS5AA",   # Families: Married-couple family ~ With own children under 18 years
    "CM9AA",   # Housing units: Occupied
    "CM9AB",   # Housing units: Vacant
    "CN1AA",   # Housing units: Owner occupied
    "CN1AB",   # Housing units: Renter occupied
    "CR0AA",   # Persons: In households ~ Under 18 years
    "D06AA",   # Persons: Under 18 years
    "CQ1AB",   # Persons: In group quarters--Noninstitutionalized
    "CM5AA",   # Families: Total
    "CM4AA",   # Households: Total
    "CM7AA",   # Housing units: Total
    "CL8AA",   # Persons: Total
    "CN0AA",   # Housing units: Vacant--For rent
    "CN0AB",   # Housing units: Vacant--For sale only
    "CN0AC",   # Housing units: Vacant--Rented or sold, not occupied
    "CN0AD",   # Housing units: Vacant--Seasonal, recreational, or occasional use
    "CN0AE",   # Housing units: Vacant--For migrant workers
    "CN0AF",   # Housing units: Vacant--Other vacant
})

# ACS choropleth: "all" in var_list, so no filtering; all go to "acs"
# No ACS_EXTRAS category.


def get_choropleth_source(source: str, variable: str) -> str:
    """
    Return the effective source for D3 export and fetch.

    For decennial: variables in DECENNIAL_CHORO_APPROVED -> "decennial";
    others -> "decennial_extras".
    For acs: always "acs" (no extras).
    """
    if source == "acs":
        return "acs"
    if source == "decennial":
        return "decennial" if variable in DECENNIAL_CHORO_APPROVED else "decennial_extras"
    return source


def is_decennial_extras_source(source: str) -> bool:
    """True if source uses decennial GeoJSON (decennial or decennial_extras)."""
    return source in ("decennial", "decennial_extras")

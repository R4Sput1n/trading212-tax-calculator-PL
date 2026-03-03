"""
Configuration for countries with double taxation treaties with Poland.

This list contains countries that have signed double taxation treaties (Umowa o Unikaniu Podwójnego Opodatkowania - UPO)
with Poland. For dividends from these countries, Poland allows foreign tax credit.

For countries NOT on this list, the full 19% Polish tax is due on the gross dividend amount,
regardless of foreign tax already paid.

Source: Ministry of Finance of Poland
Last updated: 2026
"""

# Countries with double taxation treaties with Poland (in English)
COUNTRIES_WITH_TAX_TREATY = {
    "Albania",
    "Algeria",
    "Saudi Arabia",
    "Armenia",
    "Australia",
    "Austria",
    "Azerbaijan",
    "Bangladesh",
    "Belgium",
    "Belarus",
    "Bosnia and Herzegovina",
    "Brazil",
    "Bulgaria",
    "Chile",
    "China",
    "Croatia",
    "Cyprus",
    "Montenegro",
    "Czechia",
    "Czech Republic",  # Alternative name for Czechia
    "Denmark",
    "Egypt",
    "Estonia",
    "Ethiopia",
    "Philippines",
    "Finland",
    "France",
    "Greece",
    "Georgia",
    "Guernsey",
    "Spain",
    "Netherlands",
    "India",
    "Indonesia",
    "Iran",
    "Ireland",
    "Iceland",
    "Israel",
    "Japan",
    "Jersey",
    "Jordan",
    "Canada",
    "Qatar",
    "Kazakhstan",
    "Kyrgyzstan",
    "South Korea",
    "Korea",  # Alternative name
    "Kuwait",
    "Lebanon",
    "Lithuania",
    "Luxembourg",
    "Latvia",
    "North Macedonia",
    "Macedonia",  # Alternative name
    "Malaysia",
    "Malta",
    "Morocco",
    "Mexico",
    "Moldova",
    "Mongolia",
    "Germany",
    "Nigeria",
    "Norway",
    "New Zealand",
    "Pakistan",
    "Portugal",
    "South Africa",
    "Russia",
    "Romania",
    "Serbia",
    "Singapore",
    "Slovakia",
    "Slovenia",
    "Sri Lanka",
    "United States",
    "USA",  # Alternative name
    "Syria",
    "Switzerland",
    "Sweden",
    "Tajikistan",
    "Thailand",
    "Taiwan",
    "Tunisia",
    "Turkey",
    "Ukraine",
    "Uruguay",
    "Uzbekistan",
    "Hungary",
    "United Kingdom",
    "UK",  # Alternative name
    "Great Britain",  # Alternative name
    "Vietnam",
    "Italy",
    "Isle of Man",
    "Zambia",
    "Zimbabwe",
    "United Arab Emirates",
    "UAE",  # Alternative name
}


def has_tax_treaty(country: str) -> bool:
    """
    Check if a country has a double taxation treaty with Poland.

    Args:
        country: Country name (case-insensitive)

    Returns:
        True if the country has a tax treaty with Poland, False otherwise
    """
    if not country:
        return False

    return country.strip() in COUNTRIES_WITH_TAX_TREATY or country.strip().title() in COUNTRIES_WITH_TAX_TREATY


def get_treaty_status_note(country: str) -> str:
    """
    Get a note about the tax treaty status for a country.

    Args:
        country: Country name

    Returns:
        Human-readable note about treaty status
    """
    if has_tax_treaty(country):
        return f"{country} ma umowę UPO z Polską (foreign tax credit)"
    else:
        return f"{country} NIE MA umowy UPO z Polską (pełne 19% podatku w PL)"

"""Official 2026 World Cup final draw (Groups A-L), play-offs resolved.

The December 2025 draw left six slots as play-off placeholders. The March 2026
play-offs resolved them:
  UEFA:            Czechia -> A, Bosnia and Herzegovina -> B, Turkiye -> D, Sweden -> F
  Intercontinental: Iraq -> I, DR Congo -> K

Team names below already use the martj42 dataset's spellings (e.g. Czech
Republic, Turkey, Ivory Coast, South Korea, Cape Verde) so Elo lookups resolve.
"""

OFFICIAL_GROUPS = {
    "A": ["Mexico", "South Africa", "South Korea", "Czech Republic"],
    "B": ["Canada", "Bosnia and Herzegovina", "Qatar", "Switzerland"],
    "C": ["Brazil", "Morocco", "Haiti", "Scotland"],
    "D": ["United States", "Paraguay", "Australia", "Turkey"],
    "E": ["Germany", "Curaçao", "Ivory Coast", "Ecuador"],
    "F": ["Netherlands", "Japan", "Sweden", "Tunisia"],
    "G": ["Belgium", "Egypt", "Iran", "New Zealand"],
    "H": ["Spain", "Cape Verde", "Saudi Arabia", "Uruguay"],
    "I": ["France", "Senegal", "Iraq", "Norway"],
    "J": ["Argentina", "Algeria", "Austria", "Jordan"],
    "K": ["Portugal", "DR Congo", "Uzbekistan", "Colombia"],
    "L": ["England", "Croatia", "Ghana", "Panama"],
}

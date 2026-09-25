"""Convertit les mesures ADC étalonnées en pourcentages relatifs."""
import math

# Nouveau module relevé le 23/09/2026 : ADC élevé dans le noir.
LIGHT_DARK = 1015.0
LIGHT_LIT = 220.0

# Références historiques sur 5 V ; à revérifier après le passage sur D3.
# Pleine échelle estimée par extrapolation linéaire : 478 / (2/3) ≈ 717.
# Ne pas immerger l'électronique pour chercher un point à 100 %.
WATER_DRY = 0.0
WATER_FULL = 717.0


def _percent(raw, minimum, maximum):
    """Convertit une valeur ADC valide en pourcentage borné."""
    if raw is None or not math.isfinite(raw) or not 0 <= raw <= 1023:
        return None
    value = 100 * (raw - minimum) / (maximum - minimum)
    return round(max(0, min(100, value)), 1)


def relative_light(raw):
    """0 % = couvert ; 100 % = éclairage de référence."""
    return _percent(raw, LIGHT_DARK, LIGHT_LIT)


def reservoir_level(raw):
    """0 % = sonde sèche ; 100 % = profondeur de référence."""
    return _percent(raw, WATER_DRY, WATER_FULL)

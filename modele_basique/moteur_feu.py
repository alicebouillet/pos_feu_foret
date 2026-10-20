"""Relais de compatibilité vers modele_sans_relief/moteur_simulation.py."""

import sys

from modele_sans_relief import moteur_simulation as _moteur


sys.modules[__name__] = _moteur

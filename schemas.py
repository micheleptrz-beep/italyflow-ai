"""
ItalyFlow AI — Pydantic Schemas & Enums v2.0
"""
from enum import Enum


class MarketEnum(str, Enum):
    USA = "USA"
    Cina = "Cina"
    Canada = "Canada"
    Giappone = "Giappone"
    UK = "UK"
    Italia = "Italia"
    UE = "UE"
    Corea = "Corea"
    Argentina = "Argentina"
    Brasile = "Brasile"

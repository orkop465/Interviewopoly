# board.py
from dataclasses import dataclass
from typing import Literal, List, Dict, Any

TileType = Literal[
    "START",
    "COMPANY",  # used for properties, railroads, utilities (purchase-able)
    "CHANCE",
    "COMMUNITY",
    "TAX",  # kept for compatibility if ever referenced
    "JAIL",
    "FREE_PARKING",
    "GOTO_JAIL",
]


@dataclass
class Tile:
    name: str
    ttype: TileType
    payload: Dict[str, Any]


# Helper to make a purchasable tile.
# We now tag each property with a qkind: "LC" | "SD" | "BH".
# "gate" is preserved for later monetization/ownership rules (unchanged).
def prop(name: str, price: int, gate: str, group: str, qkind: str) -> Tile:
    return Tile(name, "COMPANY", {"price": price, "gate": gate, "group": group, "qkind": qkind})


# Property groups follow classic Monopoly colors:
# BROWN, LIGHT_BLUE, PINK, ORANGE, RED, YELLOW, GREEN, DARK_BLUE
# Special purchasables:
# RR for railroads, UTIL for utilities
#
# Index orientation:
#  0 = GO (bottom-right corner)
#  move left across bottom to 9 = JAIL (bottom-left)
#  up left edge to 19 = FREE_PARKING (top-left)
#  right across top to 29 = GOTO_JAIL (top-right)
#  down right edge to 39 = back to GO
#
# Path: 0→1→...→39→0...
#
# Each color has three properties; for each color we assign one LC, one SD, one BH.

BOARD: List[Tile] = [
    # Bottom row, right to left
    Tile("GO", "START", {}),  # 0
    prop("FedEx", 60, "LC_EASY", "BROWN", "SD"),  # 1
    Tile("Community Chest", "COMMUNITY", {}),  # 2
    prop("Starbucks", 60, "LC_EASY", "BROWN", "BH"),  # 3
    # Income Tax -> third BROWN property
    prop("Target", 70, "LC_EASY", "BROWN", "LC"),  # 4
    # Railroads/utilities unchanged
    prop("NYC", 200, "LC_MED", "RR", "LC"),  # 5
    prop("Enterprise", 100, "LC_EASY", "LIGHT_BLUE", "BH"),  # 6
    Tile("Chance", "CHANCE", {}),  # 7
    prop("Nokia", 100, "LC_MED", "LIGHT_BLUE", "SD"),  # 8
    prop("Hertz", 120, "LC_MED", "LIGHT_BLUE", "LC"),  # 9  -> Jail corner next

    # Left column, bottom to top
    Tile("Jail", "JAIL", {}),  # 10
    prop("Odoo", 140, "LC_MED", "PINK", "LC"),  # 11
    prop("Utility 1", 150, "LC_MED", "UTIL", ""),  # 12
    prop("Adobe", 140, "LC_MED", "PINK", "BH"),  # 13
    prop("eBay", 160, "LC_HARD", "PINK", "SD"),  # 14
    prop("SF", 200, "LC_MED", "RR", "LC"),  # 15
    prop("Moog", 180, "LC_MED", "ORANGE", "SD"),  # 16
    Tile("Community Chest", "COMMUNITY", {}),  # 17
    prop("Valmar", 180, "LC_MED", "ORANGE", "LC"),  # 18
    prop("M&T", 200, "LC_HARD", "ORANGE", "BH"),  # 19 -> Free Parking corner

    # Top row, left to right
    Tile("Free Parking", "FREE_PARKING", {}),  # 20
    prop("IBM", 220, "LC_MED", "RED", "LC"),  # 21
    Tile("Chance", "CHANCE", {}),  # 22
    prop("AMD", 220, "LC_HARD", "RED", "SD"),  # 23
    prop("Palantir", 240, "LC_HARD", "RED", "BH"),  # 24
    prop("Austin", 200, "LC_MED", "RR", "LC"),  # 25
    prop("Tesla", 260, "LC_HARD", "YELLOW", "LC"),  # 26
    prop("Netflix", 260, "LC_HARD", "YELLOW", "BH"),  # 27
    prop("Utility 2", 150, "LC_MED", "UTIL", ""),  # 28
    prop("Samsung", 280, "LC_HARD", "YELLOW", "SD"),  # 29 -> Go To Jail corner

    # Right column, top to bottom
    Tile("Go To Jail", "GOTO_JAIL", {}),  # 30
    prop("Meta", 300, "SYS_DESIGN", "GREEN", "BH"),  # 31
    prop("Amazon", 300, "SYS_DESIGN", "GREEN", "LC"),  # 32
    Tile("Community Chest", "COMMUNITY", {}),  # 33
    prop("Google", 320, "SYS_DESIGN", "GREEN", "SD"),  # 34
    prop("Boston", 200, "LC_MED", "RR", "LC"),  # 35
    Tile("Chance", "CHANCE", {}),  # 36
    prop("Nvidia", 350, "SYS_DESIGN", "DARK_BLUE", "BH"),  # 37
    # Luxury Tax -> third DARK_BLUE property
    prop("Microsoft", 380, "SYS_DESIGN", "DARK_BLUE", "SD"),  # 38
    prop("Apple", 400, "BEHAVIORAL", "DARK_BLUE", "LC"),  # 39 back to GO next
]

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
    prop("Property 1", 60, "LC_EASY", "BROWN", "SD"),  # 1
    Tile("Community Chest", "COMMUNITY", {}),  # 2
    prop("Property 2", 60, "LC_EASY", "BROWN", "BH"),  # 3
    # Income Tax -> third BROWN property
    prop("Property 2A", 70, "LC_EASY", "BROWN", "LC"),  # 4
    # Railroads/utilities unchanged
    prop("Railroad 1", 200, "LC_MED", "RR", ""),  # 5
    prop("Property 3", 100, "LC_EASY", "LIGHT_BLUE", "BH"),  # 6
    Tile("Chance", "CHANCE", {}),  # 7
    prop("Property 4", 100, "LC_MED", "LIGHT_BLUE", "SD"),  # 8
    prop("Property 5", 120, "LC_MED", "LIGHT_BLUE", "LC"),  # 9  -> Jail corner next

    # Left column, bottom to top
    Tile("Jail", "JAIL", {}),  # 10
    prop("Property 6", 140, "LC_MED", "PINK", "LC"),  # 11
    prop("Utility 1", 150, "LC_MED", "UTIL", ""),  # 12
    prop("Property 7", 140, "LC_MED", "PINK", "BH"),  # 13
    prop("Property 8", 160, "LC_HARD", "PINK", "SD"),  # 14
    prop("Railroad 2", 200, "LC_MED", "RR", ""),  # 15
    prop("Property 9", 180, "LC_MED", "ORANGE", "SD"),  # 16
    Tile("Community Chest", "COMMUNITY", {}),  # 17
    prop("Property 10", 180, "LC_MED", "ORANGE", "LC"),  # 18
    prop("Property 11", 200, "LC_HARD", "ORANGE", "BH"),  # 19 -> Free Parking corner

    # Top row, left to right
    Tile("Free Parking", "FREE_PARKING", {}),  # 20
    prop("Property 12", 220, "LC_MED", "RED", "LC"),  # 21
    Tile("Chance", "CHANCE", {}),  # 22
    prop("Property 13", 220, "LC_HARD", "RED", "SD"),  # 23
    prop("Property 14", 240, "LC_HARD", "RED", "BH"),  # 24
    prop("Railroad 3", 200, "LC_MED", "RR", ""),  # 25
    prop("Property 15", 260, "LC_HARD", "YELLOW", "LC"),  # 26
    prop("Property 16", 260, "LC_HARD", "YELLOW", "BH"),  # 27
    prop("Utility 2", 150, "LC_MED", "UTIL", ""),  # 28
    prop("Property 17", 280, "LC_HARD", "YELLOW", "SD"),  # 29 -> Go To Jail corner

    # Right column, top to bottom
    Tile("Go To Jail", "GOTO_JAIL", {}),  # 30
    prop("Property 18", 300, "SYS_DESIGN", "GREEN", "BH"),  # 31
    prop("Property 19", 300, "SYS_DESIGN", "GREEN", "LC"),  # 32
    Tile("Community Chest", "COMMUNITY", {}),  # 33
    prop("Property 20", 320, "SYS_DESIGN", "GREEN", "SD"),  # 34
    prop("Railroad 4", 200, "LC_MED", "RR", ""),  # 35
    Tile("Chance", "CHANCE", {}),  # 36
    prop("Property 21", 350, "SYS_DESIGN", "DARK_BLUE", "BH"),  # 37
    # Luxury Tax -> third DARK_BLUE property
    prop("Property 21A", 380, "SYS_DESIGN", "DARK_BLUE", "SD"),  # 38
    prop("Property 22", 400, "BEHAVIORAL", "DARK_BLUE", "LC"),  # 39 back to GO next
]

# board.py
from dataclasses import dataclass
from typing import Literal, List, Dict, Any

TileType = Literal[
    "START",
    "LC_EASY", "LC_MED", "LC_HARD",
    "SYS_DESIGN", "BEHAVIORAL",
    "CHANCE", "COMMUNITY", "COMPANY",
    "JAIL", "FREE_PARKING", "GOTO_JAIL",
]

@dataclass
class Tile:
    name: str
    ttype: TileType
    payload: Dict[str, Any]

# 20 tiles on a 6x6 perimeter (indices are clockwise):
#
# row0:  0  1  2  3  4  5
# row1: 19           6
# row2: 18           7
# row3: 17           8
# row4: 16           9
# row5: 15 14 13 12 11 10
#
# Path: 0→1→2→3→4→5→6→7→8→9→10→11→12→13→14→15→16→17→18→19→0...

BOARD: List[Tile] = [
    Tile("Start", "START", {}),                                      # 0
    Tile("Google Ave", "COMPANY", {"price": 400, "gate": "LC_MED"}), # 1
    Tile("LeetCode Lane", "LC_EASY", {}),                            # 2
    Tile("Community Chest", "COMMUNITY", {}),                        # 3
    Tile("Jail", "JAIL", {}),                                        # 4
    Tile("Amazon Blvd", "COMPANY", {"price": 450, "gate": "LC_HARD"}), # 5

    Tile("Behavioral Bay", "BEHAVIORAL", {}),                        # 6
    Tile("LeetCode Row", "LC_MED", {}),                              # 7
    Tile("Chance", "CHANCE", {}),                                    # 8
    Tile("Free Parking", "FREE_PARKING", {}),                        # 9
    Tile("Meta Mall", "COMPANY", {"price": 420, "gate": "LC_MED"}),  # 10
    Tile("System Design Sq", "SYS_DESIGN", {}),                      # 11

    Tile("Go To Jail", "GOTO_JAIL", {}),                             # 12
    Tile("Netflix Nook", "COMPANY", {"price": 380, "gate": "LC_EASY"}), # 13
    Tile("Behavioral Pier", "BEHAVIORAL", {}),                       # 14
    Tile("LeetCode Loop", "LC_MED", {}),                             # 15
    Tile("Chance 2", "CHANCE", {}),                                  # 16
    Tile("System Design Blvd", "SYS_DESIGN", {}),                    # 17
    Tile("Behavioral Bridge", "BEHAVIORAL", {}),                     # 18
    Tile("LeetCode Tower", "LC_HARD", {}),                           # 19
]

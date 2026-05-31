"""Official 2026 World Cup knockout structure (FIFA bracket / Annex C).

This is the tournament *rulebook*, not fetched data — the matchups themselves
don't exist until the groups are played. The Round of 32 is defined by group
position:
  - Winners of C, F, H, J play runners-up (fixed pairings).
  - Winners of A, B, D, E, G, I, K, L play the 8 best third-placed teams.
  - The eight 3rd-placed slots accept a third only from a constrained set of
    groups; FIFA's Annex C lists an assignment for all C(12,8)=495 combinations.
    Rather than hardcode that table, we solve the assignment at runtime by
    bipartite matching against the allowed-group constraints — structurally
    identical (correct groups, no same-group clash) for any combination.
Source: en.wikipedia.org/wiki/2026_FIFA_World_Cup_knockout_stage
"""
from __future__ import annotations

# Which groups each 3rd-place slot may draw from (keyed by R32 match number).
THIRD_SLOTS = {
    "T74": set("ABCDF"), "T77": set("CDFGH"), "T79": set("CEFHI"),
    "T80": set("EHIJK"), "T81": set("BEFIJ"), "T82": set("AEHIJ"),
    "T85": set("EFGIJ"), "T87": set("DEIJL"),
}

# Round of 32 (matches 73-88), each as a pair of position codes.
#   "1X"/"2X" = winner/runner-up of group X; "T##" = a 3rd-place slot.
R32 = [
    ("2A", "2B"),   # 73
    ("1E", "T74"),  # 74
    ("1F", "2C"),   # 75
    ("1C", "2F"),   # 76
    ("1I", "T77"),  # 77
    ("2E", "2I"),   # 78
    ("1A", "T79"),  # 79
    ("1L", "T80"),  # 80
    ("1D", "T81"),  # 81
    ("1G", "T82"),  # 82
    ("2K", "2L"),   # 83
    ("1H", "2J"),   # 84
    ("1B", "T85"),  # 85
    ("1J", "2H"),   # 86
    ("1K", "T87"),  # 87
    ("2D", "2G"),   # 88
]

R16 = {89: (74, 77), 90: (73, 75), 91: (76, 78), 92: (79, 80),
       93: (83, 84), 94: (81, 82), 95: (86, 88), 96: (85, 87)}
QF = {97: (89, 90), 98: (93, 94), 99: (91, 92), 100: (95, 96)}
SF = {101: (97, 98), 102: (99, 100)}


def assign_thirds(thirds):
    """Match the 8 qualifying thirds to the 8 slots respecting allowed groups.

    `thirds`: list of (team, group_letter). Returns {slot_id: team}.
    """
    third_to_slot = {}                                   # third index -> slot id

    def try_assign(slot, visited):
        for i, (_, g) in enumerate(thirds):
            if g in THIRD_SLOTS[slot] and i not in visited:
                visited.add(i)
                if i not in third_to_slot or try_assign(third_to_slot[i], visited):
                    third_to_slot[i] = slot
                    return True
        return False

    # most-constrained slots first → finds the perfect matching that always exists
    for slot in sorted(THIRD_SLOTS, key=lambda s: sum(g in THIRD_SLOTS[s]
                                                      for _, g in thirds)):
        try_assign(slot, set())

    slot_to_team = {s: thirds[i][0] for i, s in third_to_slot.items()}
    if len(slot_to_team) < len(THIRD_SLOTS):             # safety net (shouldn't fire)
        used = set(third_to_slot)
        spare = [i for i in range(len(thirds)) if i not in used]
        for s, i in zip((s for s in THIRD_SLOTS if s not in slot_to_team), spare):
            slot_to_team[s] = thirds[i][0]
    return slot_to_team


def run_knockout(winners, runners, thirds, play):
    """Play the official bracket.

    winners/runners: {group_letter: team}. thirds: ranked list of (team, group),
    top 8. play(a, b) -> winner. Returns (champion, finalists, semifinalists).
    """
    pos = {f"1{g}": t for g, t in winners.items()}
    pos.update({f"2{g}": t for g, t in runners.items()})
    pos.update(assign_thirds(thirds))

    win = {}
    for i, (a, b) in enumerate(R32):
        win[73 + i] = play(pos[a], pos[b])
    for rnd in (R16, QF):
        for m, (x, y) in rnd.items():
            win[m] = play(win[x], win[y])
    semifinalists = [win[97], win[98], win[99], win[100]]
    for m, (x, y) in SF.items():
        win[m] = play(win[x], win[y])
    finalists = [win[101], win[102]]
    champion = play(win[101], win[102])
    return champion, finalists, semifinalists

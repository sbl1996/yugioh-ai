# Features

## Card 
- name+desc: 1, int, id (110)
- location: 1, int, 0: N/A, 1+: same as location2str (9)
- seq: 1, int, 0: N/A, 1+: seq in location
- owner: 1, int, 0: me, 1: oppo (2)
- position: 1, int, 0: N/A, same as position2str
- attribute: 1, int, 0: N/A, same as attribute2str[2:]
- race: 1, int, 0: N/A, same as race2str
- level: 1, int, 0: N/A
- atk: 2, max 65535 to 2 bytes
- def: 2, max 65535 to 2 bytes
- type: 25, multi-hot, same as type2str

## Global
- lp: 2, max 65535 to 2 bytes
- oppo_lp: 2, max 65535 to 2 bytes
<!-- - turn: 8, int, trunc to 8 -->
- phase: 1, int, one-hot (10)
- is_first: 1, int, 0: False, 1: True
- is_my_turn: 1, int, 0: False, 1: True

## Action
- card index: 1, int
- msg: 1, int (16)
- act: 1, int (8)
  - N/A
  - t: Set
  - r: Reposition
  - v: Activate
  - c: Special Summon
  - s: Summon Face-up Attack
  - m: Summon Face-down Defense
  - a: Attack
- yes/no: 1, int (3)
  - N/A
  - Yes
  - No
- phase: 1, int (4)
  - N/A
  - Battle (b)
  - Main Phase 2 (m)
  - End Phase (e)
- cancel: 1, int (2)
  - N/A
  - Cancel
- position: 1, int (5)
  - N/A
  - FACEUP_ATTACK
  - FACEDOWN_ATTACK
  - FACEUP_DEFENSE
  - FACEDOWN_DEFENSE
from ygo.envs.glb import register_message
from itertools import product, combinations

import io

from ygo.envs.card import Card
from ygo.constants import LOCATION
from ygo.envs.duel import Duel, Decision
from ygo.utils import parse_ints, check_sum


def msg_select_sum(duel: Duel, data):
    data = io.BytesIO(data[1:])
    mode = duel.read_u8(data)
    player = duel.read_u8(data)
    val = duel.read_u32(data)
    select_min = duel.read_u8(data)
    select_max = duel.read_u8(data)
    count = duel.read_u8(data)
    must_select = []
    for i in range(count):
        code = duel.read_u32(data)
        card = Card(code)
        card.controller = duel.read_u8(data)
        card.location = LOCATION(duel.read_u8(data))
        card.sequence = duel.read_u8(data)
        param = duel.read_u32(data)
        card.param = (param & 0xff, param >> 16)
        must_select.append(card)
    count = duel.read_u8(data)
    select_some = []
    for i in range(count):
        code = duel.read_u32(data)
        card = Card(code)
        card.controller = duel.read_u8(data)
        card.location = LOCATION(duel.read_u8(data))
        card.sequence = duel.read_u8(data)
        param = duel.read_u32(data)
        card.param = (param & 0xff, param >> 16)
        select_some.append(card)
    select_sum(duel, mode, player, val, select_min, select_max, must_select, select_some)
    return data.read()


def find_combinations(cards, expected, at_least=False):
    result = []
    for r in range(1, len(cards) + 1):
        for subset in combinations(cards, r):
            for levels in product(*[card[1] for card in subset]):
                if at_least:
                    if sum(levels) >= expected:
                        result.append(tuple(card[0] for card in subset))
                else:
                    if sum(levels) == expected:
                        result.append(tuple(card[0] for card in subset))
    return result


def select_sum(duel: Duel, mode, player, val, select_min, select_max, must_select, select_some):
    pl = duel.players[player]

    must_select_levels = []

    if len(must_select) == 1:
        must_select_levels = list(must_select[0].param)
    elif len(must_select) > 1:
        for i in range(len(must_select)):
            if i == len(must_select) - 1:
                break
            c = must_select[i]
            for j in range(i + 1, len(must_select)):
                c2 = must_select[j]
                for l in c.param:
                    for l2 in c2.param:
                        must_select_levels.append(l + l2)
    else:
        must_select_levels = [0]

    if len(must_select_levels) > 1:
        must_select_levels = sorted(set(filter(lambda l: l, must_select_levels)))

    card_levels = [
        (i + 1, [p for p in card.param if p > 0]) for i, card in enumerate(select_some)
    ]

    def prompt():
        if mode == 0:
            if len(must_select_levels) == 1:
                expected = val - must_select_levels[0]
                options = find_combinations(card_levels, expected)
                options = list(set(options))
                options = [" ".join(str(i) for i in ints) for ints in options]
                pl.notify(pl._("Select cards with a total value of %d, seperated by spaces.") % (expected))
            else:
                options = []
                for l in must_select_levels:
                    expected = val - l
                    options.extend(find_combinations(card_levels, expected))
                options = list(set(options))
                options = [" ".join(str(i) for i in ints) for ints in options]				
                pl.notify(pl._("Select cards with a total value being one of the following, seperated by spaces: %s") % (', '.join([str(val - l) for l in must_select_levels])))
        else:
            expected = val - must_select_levels[0]
            options = find_combinations(card_levels, expected, at_least=True)
            options = list(set(options))
            options = [" ".join(str(i) for i in ints) for ints in options]
            pl.notify(pl._("Select cards with a total value of at least %d, seperated by spaces.") % (val - must_select_levels[0]))
        for c in must_select:
            pl.notify(pl._("%s must be selected, automatically selected.") % c.get_name())
        for i, card in enumerate(select_some):
            pl.notify("%d: %s (%s)" % (i+1, card.get_name(), (' ' + pl._('or') + ' ').join([str(p) for p in card.param if p > 0])))
        return pl.notify(Decision, r, options)

    def error(t):
        pl.notify(t)
        return prompt()

    def r(caller):
        ints = [i - 1 for i in parse_ints(caller.text)]
        if len(ints) != len(set(ints)):
            return error(pl._("Duplicate values not allowed."))
        if any((i < 0) or (i > len(select_some) - 1) for i in ints):
            return error(pl._("Value out of range."))
        selected = [select_some[i] for i in ints]
        s = []

        for i in range(len(selected)):
            if i == len(selected) - 1:
                break
            c = selected[i]
            for j in range(i + 1, len(selected)):
                c2 = selected[j]
                for l in c.param:
                    for l2 in c2.param:
                        s.append(l + l2)
        
        s = sorted(set(s))

        if mode == 1 and not check(must_select + selected, val):
            return error(pl._("Levels out of range."))
        if mode == 0 and not any([check_sum(selected, val - m) for m in must_select_levels]):
            return error(pl._("Selected value does not equal %d.") % (val,))
        lst = [len(ints) + len(must_select)]
        lst.extend([0] * len(must_select))
        lst.extend(ints)
        b = bytearray(lst)
        duel.set_responseb(b)
    prompt()


def check(cards, acc):
    sum = 0
    mx = 0
    mn = 0x7fffffff
    for c in cards:
        o1 = c.param[0]
        o2 = c.param[1]
        if o2 and o2 < o1:
            ms = o2
        else:
            ms = o1
        sum += ms
        mx += max(o2, o1)
        if ms < mn:
            mn = ms
    if mx < acc or sum - mn >= acc:
        return False
    return True

register_message({23: msg_select_sum})



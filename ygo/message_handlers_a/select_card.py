from itertools import combinations

import io

from ygo.card import Card
from ygo.constants import LOCATION
from ygo.duel import Duel, ActionRequired
from ygo.utils import parse_ints


def msg_select_tribute(duel: Duel, data):
    data = io.BytesIO(data[1:])
    player = duel.read_u8(data)
    cancelable = duel.read_u8(data)
    min = duel.read_u8(data)
    max = duel.read_u8(data)
    size = duel.read_u8(data)
    cards = []
    for i in range(size):
        code = duel.read_u32(data)
        card = Card(code)
        card.controller = duel.read_u8(data)
        card.location = LOCATION(duel.read_u8(data))
        card.sequence = duel.read_u8(data)
        card.position = duel.get_card(
            card.controller, card.location, card.sequence
        ).position
        card.release_param = duel.read_u8(data)
        cards.append(card)

    options, r = select_tribute(duel, player, cancelable, min, max, cards)
    return ActionRequired("select_tribute", options, r, data.read())


def msg_select_card(duel: Duel, data):
    data = io.BytesIO(data[1:])
    player = duel.read_u8(data)
    cancelable = duel.read_u8(data)
    min = duel.read_u8(data)
    max = duel.read_u8(data)
    size = duel.read_u8(data)
    cards = []
    for i in range(size):
        code = duel.read_u32(data)
        loc = duel.read_u32(data)
        card = Card(code)
        card.set_location(loc)
        cards.append(card)
    options, r = select_card(duel, player, cancelable, min, max, cards)
    return ActionRequired("select_card", options, r, data.read())


def select_card(
    duel: Duel, player: int, cancelable, min_cards, max_cards, cards, is_tribute=False
):
    pl = duel.players[player]
    pl.card_list = cards

    def prompt():
        if is_tribute:
            pl.notify(
                pl._("Select %d to %d cards to tribute separated by spaces:")
                % (min_cards, max_cards)
            )
        else:
            pl.notify(
                pl._("Select %d to %d cards separated by spaces:") % (min_cards, max_cards)
            )
        options = []
        for i, c in enumerate(cards):
            name = duel.cardlist_info_for_player(c, pl)
            options.append(i + 1)
            pl.notify("%d: %s" % (i + 1, name))
        combs = []
        for t in range(min_cards, max_cards + 1):
            combs += [" ".join([ str(x) for x in comb]) for comb in combinations(options, t)]
        return combs, r

    def r(caller):
        cds = [i - 1 for i in parse_ints(caller.text)]
        if len(cds) != len(set(cds)):
            raise ValueError("Duplicate values not allowed.")
        if (not is_tribute and len(cds) < min_cards) or len(cds) > max_cards:
            raise ValueError("Invalid number of cards.")
        if cds and (min(cds) < 0 or max(cds) > len(cards) - 1):
            raise ValueError("Invalid card index.")
        buf = bytes([len(cds)])
        tribute_value = 0
        for i in cds:
            tribute_value += cards[i].release_param if is_tribute else 0
            buf += bytes([i])
        if is_tribute and tribute_value < min_cards:
            raise ValueError("Not enough tributes.")
        duel.set_responseb(buf)
    return prompt()


def select_tribute(duel: Duel, *args, **kwargs):
    kwargs["is_tribute"] = True
    return select_card(duel, *args, **kwargs)


MESSAGES = {15: msg_select_card, 20: msg_select_tribute}

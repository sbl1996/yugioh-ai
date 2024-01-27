from ygo.envs.glb import register_message
from itertools import combinations

import io

from ygo.envs.card import Card
from ygo.constants import LOCATION
from ygo.envs.duel import Duel, ActionRequired
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
    return ActionRequired("select_tribute", player, options, r, data.read())


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
    return ActionRequired("select_card", player, options, r, data.read())


def select_card(
    duel: Duel, player: int, cancelable, min_cards, max_cards, cards, is_tribute=False
):
    pl = duel.players[player]
    pl.card_list = cards

    if duel.verbose:
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
    spec2i = {}
    for i, c in enumerate(cards):
        spec = c.get_spec(pl)
        options.append(spec)
        spec2i[spec] = i
        if duel.verbose:
            name = duel.cardlist_info_for_player(c, pl)
            pl.notify("%s: %s" % (spec, name))
    combs = []
    for t in range(min_cards, max_cards + 1):
        combs += [" ".join(comb) for comb in combinations(options, t)]

    def r(caller):
        cds = [spec2i[s] for s in caller.text.split(" ")]
        if (not is_tribute and len(cds) < min_cards) or len(cds) > max_cards:
            raise ValueError("Invalid number of cards.")
        if cds and (min(cds) < 0 or max(cds) > len(cards) - 1):
            raise ValueError("Invalid card index.")
        buf = bytearray(1 + len(cds))
        buf[0] = len(cds)
        tribute_value = 0
        for k, i in enumerate(cds):
            tribute_value += cards[i].release_param if is_tribute else 0
            buf[k + 1] = i
        if is_tribute and tribute_value < min_cards:
            raise ValueError("Not enough tributes.")
        duel.set_responseb(buf)

    return combs, r


def select_tribute(duel: Duel, *args, **kwargs):
    kwargs["is_tribute"] = True
    return select_card(duel, *args, **kwargs)


register_message({15: msg_select_card, 20: msg_select_tribute})

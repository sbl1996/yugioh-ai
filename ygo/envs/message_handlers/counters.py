import io

from ygo.constants import LOCATION
from ygo.envs.duel import Duel


def msg_counters(duel: Duel, data):
    data = io.BytesIO(data[0:])
    msg = duel.read_u8(data)
    ctype = duel.read_u16(data)
    pl = duel.read_u8(data)
    loc = LOCATION(duel.read_u8(data))
    seq = duel.read_u8(data)
    count = duel.read_u16(data)
    card = duel.get_card(pl, loc, seq)
    counters(duel, card, ctype, count, msg == 101)
    return data.read()


def counters(duel: Duel, card, type, count, added):
    for pl in duel.players:
        stype = duel.strings['counter'].get(type, 'Counter %d' % type)
        if added:
             pl.notify(pl._("{amount} counters of type {counter} placed on {card}").format(amount=count, counter=stype, card=card.get_name()))
        else:
             pl.notify(pl._("{amount} counters of type {counter} removed from {card}").format(amount=count, counter=stype, card=card.get_name()))


MESSAGES = {101: msg_counters, 102: msg_counters}



import io

from ygo.card import Card
from ygo.duel import Duel, Decision


def msg_select_effectyn(duel: Duel, data):
    data = io.BytesIO(data[1:])
    player = duel.read_u8(data)
    card = Card(duel.read_u32(data))
    card.set_location(duel.read_u32(data))
    desc = duel.read_u32(data)
    select_effectyn(duel, player, card, desc)
    return data.read()


def select_effectyn(duel: Duel, player: int, card, desc):
    pl = duel.players[player]
    spec = card.get_spec(pl)
    question = pl._("Do you want to use the effect from {card} in {spec}?").format(card=card.get_name(pl), spec=spec)
    s = card.get_effect_description(pl, desc, True)
    if s != '':
        question += '\n'+s

    def prompt():
        pl.notify(question)
        pl.notify(Decision, r, ['y', 'n'])

    def r(caller):
        if caller.text.lower().startswith('y'):
            duel.set_responsei(1)
        elif caller.text.lower().startswith('n'):
            duel.set_responsei(0)
        else:
            prompt()

    prompt()

MESSAGES = {12: msg_select_effectyn}

CALLBACKS = {'select_effectyn': select_effectyn}

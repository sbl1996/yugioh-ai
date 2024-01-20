from ygo.envs.glb import register_message
import io

from ygo.envs.card import Card
from ygo.envs.duel import Duel, Decision


def msg_select_effectyn(duel: Duel, data):
    data = io.BytesIO(data[1:])
    player = duel.read_u8(data)
    card = Card(duel.read_u32(data))
    card.set_location(duel.read_u32(data))
    desc = duel.read_u32(data)
    select_effectyn(duel, player, card, desc)
    return data.read()


def select_effectyn(duel: Duel, player: int, card, desc):
    if duel.verbose:
        pl = duel.players[player]
        spec = card.get_spec(pl)
        card_name = card.get_name()
        # question = pl._("Do you want to use the effect from {card} in {spec}?").format(card=card_name, spec=spec)
        if desc == 221:
            s = duel.strings['system'].get(desc) % (spec, card_name)
        elif desc == 0:
            s = duel.strings['system'].get(200) % (spec, card_name)
        elif desc < 2048:
            s = duel.strings['system'].get(desc)
            to_formats = s.count('[%ls]')
            if to_formats == 0:
                pass
            elif s.count('[%ls]') == 1:
                s = s % (card_name,)
            else:
                raise NotImplementedError("desc: %d, code: %d, string: %s" % (desc, card.code, s))
        else:
            raise NotImplementedError("desc: %d, code: %d" % (desc, card.code))
            # s = card.get_effect_description(pl, desc, True)
        # if s != '':
        question = s

    def prompt():
        if duel.verbose:
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

register_message({12: msg_select_effectyn})



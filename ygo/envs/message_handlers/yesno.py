import io

from ygo.envs.card import Card
from ygo.envs.duel import Duel, ActionRequired


def msg_yesno(duel: Duel, data):
    data = io.BytesIO(data[1:])
    player = duel.read_u8(data)
    desc = duel.read_u32(data)
    options, r = yesno(duel, player, desc)
    return ActionRequired("yesno", options, r, data.read())


def yesno(duel: Duel, player: int, desc):
    pl = duel.players[player]
    if desc > 10000:
        code = desc >> 4
        card = Card(code)
        opt = card.get_strings()[desc & 0xf]
        if opt == '':
            opt = pl._('Unknown question from %s. Yes or no?')%(card.get_name())
    else:
        opt = "String %d" % desc
        opt = duel.strings['system'].get(desc, opt)

    def r(caller):
        if caller.text.lower().startswith('y'):
            duel.set_responsei(1)
        elif caller.text.lower().startswith('n'):
            duel.set_responsei(0)
        else:
            raise ValueError("Invalid response")

    pl.notify(opt)
    pl.notify(pl._("Please enter y or n."))
    options = ['y', 'n']
    return options, r


MESSAGES = {13: msg_yesno}



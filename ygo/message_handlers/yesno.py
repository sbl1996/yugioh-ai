import io

from ygo.card import Card
from ygo.duel import Duel
from ygo.duel_reader import DuelReader


def msg_yesno(duel: Duel, data):
    data = io.BytesIO(data[1:])
    player = duel.read_u8(data)
    desc = duel.read_u32(data)
    duel.cm.call_callbacks("yesno", player, desc)
    return data.read()


def yesno(duel: Duel, player, desc):
    pl = duel.players[player]
    if desc > 10000:
        code = desc >> 4
        card = Card(code)
        opt = card.get_strings(pl)[desc & 0xf]
        if opt == '':
            opt = pl._('Unknown question from %s. Yes or no?')%(card.get_name(pl))
    else:
        opt = "String %d" % desc
        opt = pl.strings['system'].get(desc, opt)

    def prompt():
        pl.notify(opt)
        pl.notify(pl._("Please enter y or n."))
        pl.notify(DuelReader, r, ['y', 'n'])

    def r(caller):
        if caller.text.lower().startswith('y'):
            duel.set_responsei(1)
        elif caller.text.lower().startswith('n'):
            duel.set_responsei(0)
        else:
            prompt()

    prompt()

MESSAGES = {13: msg_yesno}

CALLBACKS = {'yesno': yesno}

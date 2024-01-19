import io

from ygo.constants import TYPE
from ygo.duel import Duel, ActionRequired, Player


def msg_select_battlecmd(duel: Duel, data):
    duel.state = "battle"
    data = io.BytesIO(data[1:])
    player = duel.read_u8(data)
    duel.activatable = duel.read_cardlist(data, True)
    duel.attackable = duel.read_cardlist(data, True, True)
    duel.to_m2 = duel.read_u8(data)
    duel.to_ep = duel.read_u8(data)
    pl = duel.players[player]
    options, r = select_battlecmd(duel, pl)
    return ActionRequired("select_battlecmd", options, r, data.read())


def select_battlecmd(duel: Duel, pl: Player):
    options = []
    specs = {}
    specs = {}
    pl.notify(pl._("Battle menu:"))
    for c in duel.attackable:
        spec = c.get_spec(pl)
        if c.type & TYPE.LINK:
            pl.notify(pl._("attack %s: %s (%d)") % (spec, c.get_name(pl), c.attack))
        else:
            pl.notify("attack %s: %s (%d/%d)" % (spec, c.get_name(pl), c.attack, c.defense))
        option = "a " + spec
        specs[option] = c
        options.append(option)
    if duel.activatable:
        spec = c.get_spec(pl)
        pl.notify("activate %s: %s (%d/%d)" % (spec, c.get_name(pl), c.attack, c.defense))
        option = "c " + spec
        specs[option] = c
        options.append(option)
    if duel.to_m2:
        options.append("m")
        pl.notify(pl._("m: Main phase 2."))
    if duel.to_ep:
        # always go to m2 if possible
        # if not duel.to_m2:
        options.append("e")
        pl.notify(pl._("e: End phase."))

    def r(caller):
        if caller.text in specs:
            card = specs[caller.text]
            if caller.text[0] == "c":
                seq = duel.activatable.index(card)
                duel.set_responsei((seq << 16))
            elif caller.text[0] == "a":
                seq = duel.attackable.index(card)
                duel.set_responsei((seq << 16) + 1)
        elif caller.text == "e" and duel.to_ep:
            duel.set_responsei(3)
        elif caller.text == "m" and duel.to_m2:
            duel.set_responsei(2)
        else:
            raise ValueError("Invalid option.")
    return options, r


MESSAGES = {10: msg_select_battlecmd}

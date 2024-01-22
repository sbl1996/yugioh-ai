from ygo.envs.glb import register_message
import io

from ygo.constants import TYPE
from ygo.envs.duel import Duel, ActionRequired, Player


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
    return ActionRequired("select_battlecmd", player, options, r, data.read())


def select_battlecmd(duel: Duel, pl: Player):
    options = []
    specs = {}
    specs = {}
    if duel.verbose:
        pl.notify(pl._("Battle menu:"))
    for c in duel.attackable:
        spec = c.get_spec(pl)
        if duel.verbose:
            if c.type & TYPE.LINK:
                pl.notify(pl._("%s a: %s (%d) attack") % (spec, c.get_name(), c.attack))
            else:
                pl.notify("%s a: %s (%d/%d) attack" % (spec, c.get_name(), c.attack, c.defense))
        option = spec + " a"
        specs[option] = c
        options.append(option)
    if duel.activatable:
        spec = c.get_spec(pl)
        if duel.verbose:
            pl.notify("%s v: activate %s (%d/%d)" % (spec, c.get_name(), c.attack, c.defense))
        option = spec + " v"
        specs[option] = c
        options.append(option)
    if duel.to_m2:
        options.append("m")
        if duel.verbose:
            pl.notify(pl._("m: Main phase 2."))
    if duel.to_ep:
        # always go to m2 if possible
        if not duel.to_m2:
            options.append("e")
            if duel.verbose:
                pl.notify(pl._("e: End phase."))

    def r(caller):
        if caller.text in specs:
            card = specs[caller.text]
            if caller.text[-1] == "v":
                seq = duel.activatable.index(card)
                duel.set_responsei((seq << 16))
            elif caller.text[-1] == "a":
                seq = duel.attackable.index(card)
                duel.set_responsei((seq << 16) + 1)
        elif caller.text == "e" and duel.to_ep:
            duel.set_responsei(3)
        elif caller.text == "m" and duel.to_m2:
            duel.set_responsei(2)
        else:
            raise ValueError("Invalid option.")
    return options, r


register_message({10: msg_select_battlecmd})

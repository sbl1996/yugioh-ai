from ygo.duel_reader import DuelReader
from ygo.duel import Duel


def display_battle_menu(duel: Duel, pl):
    options = []
    aspecs = {}
    cspecs = {}
    pl.notify(pl._("Battle menu:"))
    if duel.attackable:
        aspecs = {"a"+c.get_spec(pl):c for c in duel.attackable}
        # options.extend(aspecs)
        options.append("a")
        pl.notify(pl._("a: Attack."))
    if duel.activatable:
        cspecs = {"c"+c.get_spec(pl):c for c in duel.activatable}
        # options.extend(cspecs)
        options.append("c")
        pl.notify(pl._("c: activate."))
    if duel.to_m2:
        options.append("m")
        pl.notify(pl._("m: Main phase 2."))
    if duel.to_ep:
        # always go to m2 if possible
        # if not duel.to_m2:
        options.append("e")
        pl.notify(pl._("e: End phase."))

    def r(caller):
        if caller.text == "a" and duel.attackable:
            duel.battle_attack(caller.connection.player)
        elif caller.text == "c" and duel.activatable:
            duel.battle_activate(caller.connection.player)
        elif caller.text == "e" and duel.to_ep:
            duel.set_responsei(3)
        elif caller.text == "m" and duel.to_m2:
            duel.set_responsei(2)
        # elif caller.text in aspecs and duel.attackable:
        #     card = aspecs[caller.text]
        #     seq = duel.attackable.index(card)
        #     duel.set_responsei((seq << 16) + 1)
        # elif caller.text in cspecs and duel.activatable:
        #     card = cspecs[caller.text]
        #     seq = duel.activatable.index(card)
        #     duel.set_responsei((seq << 16))
        else:
            pl.notify(pl._("Invalid option."))
            return duel.display_battle_menu(pl)

    pl.notify(
        DuelReader,
        r,
        options,
    )


METHODS = {"display_battle_menu": display_battle_menu}

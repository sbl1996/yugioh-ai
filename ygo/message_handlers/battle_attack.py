from ygo.constants import TYPE
from ygo.duel import Duel, Decision, Player


def battle_attack(duel: Duel, pl: Player):
    pl.notify(pl._("Select card to attack with:"))
    specs = {}
    for c in duel.attackable:
        spec = c.get_spec(pl)
        if c.type & TYPE.LINK:
            pl.notify(pl._("%s: %s (%d)") % (spec, c.get_name(pl), c.attack))
        else:
            pl.notify("%s: %s (%d/%d)" % (spec, c.get_name(pl), c.attack, c.defense))
        specs[spec] = c
    pl.notify(pl._("z: back."))

    def r(caller):
        if caller.text == "z":
            duel.display_battle_menu(pl)
            return
        if caller.text not in specs:
            pl.notify(pl._("Invalid cardspec. Retry."))
            return duel.battle_attack(pl)
        card = specs[caller.text]
        seq = duel.attackable.index(card)
        duel.set_responsei((seq << 16) + 1)

    pl.notify(
        Decision,
        r,
        list(specs.keys()),
    )


METHODS = {"battle_attack": battle_attack}

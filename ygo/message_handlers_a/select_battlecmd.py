import io

from ygo.constants import TYPE
from ygo.duel import Duel, Decision, Player


def msg_select_battlecmd(duel: Duel, data):
	data = io.BytesIO(data[1:])
	player = duel.read_u8(data)
	activatable = duel.read_cardlist(data, True)
	attackable = duel.read_cardlist(data, True, True)
	to_m2 = duel.read_u8(data)
	to_ep = duel.read_u8(data)
	select_battlecmd(duel, player, activatable, attackable, to_m2, to_ep)
	return data.read()


def display_battle_menu(duel: Duel, pl: Player):
    options = []
    aspecs = {}
    cspecs = {}
    pl.notify(pl._("Battle menu:"))
    if duel.attackable:
        aspecs = {"a" + c.get_spec(pl): c for c in duel.attackable}
        # options.extend(aspecs)
        options.append("a")
        pl.notify(pl._("a: Attack."))
    if duel.activatable:
        cspecs = {"c" + c.get_spec(pl): c for c in duel.activatable}
        # options.extend(cspecs)
        options.append("c")
        pl.notify(pl._("c: Activate."))
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
            battle_attack(duel, pl)
        elif caller.text == "c" and duel.activatable:
            battle_activate(duel, pl)
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
            return display_battle_menu(duel, pl)

    pl.notify(
        Decision,
        r,
        options,
    )


def battle_activate(duel: Duel, pl: Player):
	pln = pl.duel_player
	pl.notify(pl._("Select card to activate:"))

	specs = {}
	for c in duel.activatable:
		spec = c.get_spec(pl)
		pl.notify("%s: %s (%d/%d)" % (spec, c.get_name(pl), c.attack, c.defense))
		specs[spec] = c

	pl.notify(pl._("z: back."))

	options = []
	# options.append('z')
	for s in specs:
		options.append(s)

	def r(caller):
		if caller.text == 'z':
			display_battle_menu(duel, pl)
			return
		if caller.text not in specs:
			pl.notify(pl._("Invalid cardspec. Retry."))
			pl.notify(Decision, r, options)
			return
		card = specs[caller.text]
		seq = duel.activatable.index(card)
		duel.set_responsei((seq << 16))
	
	pl.notify(Decision, r, options)


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
            display_battle_menu(duel, pl)
            return
        if caller.text not in specs:
            pl.notify(pl._("Invalid cardspec. Retry."))
            return battle_attack(duel, pl)
        card = specs[caller.text]
        seq = duel.attackable.index(card)
        duel.set_responsei((seq << 16) + 1)

    pl.notify(
        Decision,
        r,
        list(specs.keys()),
    )


def select_battlecmd(duel: Duel, player: int, activatable, attackable, to_m2, to_ep):
	duel.state = "battle"
	duel.activatable = activatable
	duel.attackable = attackable
	duel.to_m2 = bool(to_m2)
	duel.to_ep = bool(to_ep)
	pl = duel.players[player]
	display_battle_menu(duel, pl)


MESSAGES = {10: msg_select_battlecmd}

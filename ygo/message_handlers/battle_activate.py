from ygo.duel import Duel, Decision, Player


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
	options.append('z')
	for s in specs:
		options.append(s)

	def r(caller):
		if caller.text == 'z':
			duel.display_battle_menu(pl)
			return
		if caller.text not in specs:
			pl.notify(pl._("Invalid cardspec. Retry."))
			pl.notify(Decision, r, options)
			return
		card = specs[caller.text]
		seq = duel.activatable.index(card)
		duel.set_responsei((seq << 16))
	
	pl.notify(Decision, r, options)

METHODS = {'battle_activate': battle_activate}

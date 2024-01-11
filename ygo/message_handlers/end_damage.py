from ygo.duel import Duel

def msg_end_damage(duel: Duel, data):
	end_damage(duel)
	return data[1:]

def end_damage(duel: Duel):
	for pl in duel.players:
		pl.notify(pl._("end damage"))

MESSAGES = {114: msg_end_damage}

CALLBACKS = {'end_damage': end_damage}

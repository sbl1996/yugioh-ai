from ygo.duel import Duel

def msg_begin_damage(duel: Duel, data):
	begin_damage(duel)
	return data[1:]

def begin_damage(duel: Duel):
	for pl in duel.players:
		pl.notify(pl._("begin damage"))

MESSAGES = {113: msg_begin_damage}



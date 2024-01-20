from ygo.envs.glb import register_message
from ygo.envs.duel import Duel

def msg_begin_damage(duel: Duel, data):
	begin_damage(duel)
	return data[1:]

def begin_damage(duel: Duel):
	if not duel.verbose:
		return

	for pl in duel.players:
		pl.notify(pl._("begin damage"))

register_message({113: msg_begin_damage})



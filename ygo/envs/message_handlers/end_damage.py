from ygo.envs.glb import register_message
from ygo.envs.duel import Duel

def msg_end_damage(duel: Duel, data):
	end_damage(duel)
	return data[1:]

def end_damage(duel: Duel):
	if not duel.verbose:
		return
	for pl in duel.players:
		pl.notify(pl._("end damage"))

register_message({114: msg_end_damage})



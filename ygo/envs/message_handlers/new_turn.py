from ygo.envs.glb import register_message
from ygo.envs.duel import Duel


def msg_new_turn(duel: Duel, data):
	tp = int(data[1])
	new_turn(duel, tp)
	return data[2:]

def new_turn(duel: Duel, tp):
	duel.tp = tp
	if not duel.verbose:
		return
	duel.players[tp].notify(duel.players[tp]._("Your turn."))
	op = duel.players[1 - tp]
	op.notify(op._("%s's turn.") % duel.players[tp].nickname)

register_message({40: msg_new_turn})




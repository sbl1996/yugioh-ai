from ygo.envs.glb import register_message
import io

def msg_pay_lpcost(duel, data):
	data = io.BytesIO(data[1:])
	player = duel.read_u8(data)
	cost = duel.read_u32(data)
	pay_lpcost(duel, player, cost)
	return data.read()

def pay_lpcost(duel, player, cost):
	duel.lp[player] -= cost

	if not duel.verbose:
		return
	duel.players[player].notify(duel.players[player]._("You pay %d LP. Your LP is now %d.") % (cost, duel.lp[player]))
	players = [duel.players[1 - player]]
	for pl in players:
		pl.notify(pl._("%s pays %d LP. Their LP is now %d.") % (duel.players[player].nickname, cost, duel.lp[player]))

register_message({100: msg_pay_lpcost})



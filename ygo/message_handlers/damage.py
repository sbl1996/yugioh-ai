import io
from ygo.duel import Duel


def msg_damage(duel: Duel, data):
	data = io.BytesIO(data[1:])
	player = duel.read_u8(data)
	amount = duel.read_u32(data)
	damage(duel, player, amount)
	return data.read()


def damage(duel: Duel, player: int, amount):
	new_lp = duel.lp[player]-amount
	pl = duel.players[player]
	op = duel.players[1 - player]
	pl.notify(pl._("Your lp decreased by %d, now %d") % (amount, new_lp))
	op.notify(op._("%s's lp decreased by %d, now %d") % (duel.players[player].nickname, amount, new_lp))
	duel.lp[player] -= amount


MESSAGES = {91: msg_damage}



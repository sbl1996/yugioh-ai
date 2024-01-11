import io
from ygo.duel import Duel


def msg_hint(duel: Duel, data):
	data = io.BytesIO(data[1:])
	msg = duel.read_u8(data)
	player = duel.read_u8(data)
	value = duel.read_u32(data)
	hint(duel, msg, player, value)
	return data.read()


def hint(duel: Duel, msg, player: int, data):
	op = duel.players[1 - player]
	if msg == 3 and data in duel.strings['system']:
		duel.players[player].notify(duel.strings['system'][data])
	elif msg == 6 or msg == 7 or msg == 8:
		pass
	elif msg == 9:
		op.notify(op.strings['system'][1512] % data)

MESSAGES = {2: msg_hint}



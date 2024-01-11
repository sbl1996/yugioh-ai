import io

from ygo.duel import Duel


def msg_toss_coin(duel: Duel, data, dice=False):
	data = io.BytesIO(data[1:])
	player = duel.read_u8(data)
	count = duel.read_u8(data)
	options = [duel.read_u8(data) for i in range(count)]
	if dice:
		toss_dice(duel, player, options)
	else:
		toss_coin(duel, player, options)
	return data.read()

def toss_coin(duel: Duel, player, options):
	players = []
	players.extend(duel.players)
	for pl in players:
		s = duel.strings['system'][1623] + " "
		opts = [duel.strings['system'][60] if opt else duel.strings['system'][61] for opt in options]
		s += ", ".join(opts)
		pl.notify(s)

def toss_dice(duel: Duel, player, options):
	opts = [str(opt) for opt in options]
	players = []
	players.extend(duel.players)
	for pl in players:
		s = duel.strings['system'][1624] + " "
		s += ", ".join(opts)
		pl.notify(s)

def msg_toss_dice(duel: Duel, *args, **kwargs):
	kwargs['dice'] = True
	duel.msg_toss_coin(*args, **kwargs)

MESSAGES = {130: msg_toss_coin, 131: msg_toss_dice}



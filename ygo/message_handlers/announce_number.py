import io

from ygo.duel import Duel, Decision
from ygo.utils import parse_ints


def msg_announce_number(duel: Duel, data):
	data = io.BytesIO(data[1:])
	player = duel.read_u8(data)
	size = duel.read_u8(data)
	opts = [duel.read_u32(data) for i in range(size)]
	announce_number(duel, player, opts)
	return data.read()

def announce_number(duel: Duel, player: int, opts):
	pl = duel.players[player]
	str_opts = [str(i) for i in opts]
	def prompt():
		pl.notify(pl._("Select a number, one of: {opts}")
			.format(opts=", ".join(str_opts)))
		return pl.notify(Decision, r, str_opts)
	def r(caller):
		ints = parse_ints(caller.text)
		if not ints or ints[0] not in opts:
			return prompt()
		duel.set_responsei(opts.index(ints[0]))
	prompt()

MESSAGES = {143: msg_announce_number}



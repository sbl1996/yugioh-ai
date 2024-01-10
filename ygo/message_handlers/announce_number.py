import io

from ygo.duel_reader import DuelReader
from ygo.utils import parse_ints


def msg_announce_number(self, data):
	data = io.BytesIO(data[1:])
	player = self.read_u8(data)
	size = self.read_u8(data)
	opts = [self.read_u32(data) for i in range(size)]
	self.cm.call_callbacks('announce_number', player, opts)
	return data.read()

def announce_number(self, player, opts):
	pl = self.players[player]
	str_opts = [str(i) for i in opts]
	def prompt():
		pl.notify(pl._("Select a number, one of: {opts}")
			.format(opts=", ".join(str_opts)))
		return pl.notify(DuelReader, r, str_opts)
	def r(caller):
		ints = parse_ints(caller.text)
		if not ints or ints[0] not in opts:
			return prompt()
		self.set_responsei(opts.index(ints[0]))
	prompt()

MESSAGES = {143: msg_announce_number}

CALLBACKS = {'announce_number': announce_number}

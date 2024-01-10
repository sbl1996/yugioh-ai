import io


def msg_hint(self, data):
	data = io.BytesIO(data[1:])
	msg = self.read_u8(data)
	player = self.read_u8(data)
	value = self.read_u32(data)
	self.cm.call_callbacks('hint', msg, player, value)
	return data.read()


def hint(self, msg, player, data):
	pl = self.players[player]
	op = self.players[1 - player]
	if msg == 3 and data in pl.strings['system']:
		self.players[player].notify(pl.strings['system'][data])
	elif msg == 6 or msg == 7 or msg == 8:
		pass
	elif msg == 9:
		op.notify(op.strings['system'][1512] % data)

MESSAGES = {2: msg_hint}

CALLBACKS = {'hint': hint}

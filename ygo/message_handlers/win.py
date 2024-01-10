import io

def msg_win(self, data):
	data = io.BytesIO(data[1:])
	player = self.read_u8(data)
	reason = self.read_u8(data)
	self.cm.call_callbacks('win', player, reason)
	return data.read()

def win(self, player, reason):
	if player == 2:
		self.room.announce_draw()
		self.end()
		return

	winners = [self.players[player]]
	losers = [self.players[1 - player]]

	l_reason = lambda p: p.strings['victory'][reason]

	for w in winners:
		w.notify(w._("You won (%s).") % l_reason(w))
	for l in losers:
		l.notify(l._("You lost (%s).") % l_reason(l))

	self.end()

MESSAGES = {5: msg_win}

CALLBACKS = {'win': win}

import io

def msg_pay_lpcost(self, data):
	data = io.BytesIO(data[1:])
	player = self.read_u8(data)
	cost = self.read_u32(data)
	pay_lpcost(self, player, cost)
	return data.read()

def pay_lpcost(self, player, cost):
	self.lp[player] -= cost
	self.players[player].notify(self.players[player]._("You pay %d LP. Your LP is now %d.") % (cost, self.lp[player]))
	players = [self.players[1 - player]]
	for pl in players:
		pl.notify(pl._("%s pays %d LP. Their LP is now %d.") % (self.players[player].nickname, cost, self.lp[player]))

MESSAGES = {100: msg_pay_lpcost}



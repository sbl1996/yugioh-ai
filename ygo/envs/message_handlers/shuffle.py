from ygo.envs.glb import register_message
import io

def msg_shuffle(self, data):
	data = io.BytesIO(data[1:])
	player = self.read_u8(data)
	shuffle(self, player)
	return data.read()

def shuffle(self, player):
	if not duel.verbose:
		return
	pl = self.players[player]
	pl.notify(pl._("you shuffled your deck."))
	for pl in [self.players[1 - player]]:
		pl.notify(pl._("%s shuffled their deck.")%(self.players[player].nickname))

register_message({32: msg_shuffle})



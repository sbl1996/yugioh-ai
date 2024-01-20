from ygo.envs.glb import register_message
def msg_reversedeck(self, data):
	if self.verbose:
		for pl in self.players:
			pl.notify(pl._("all decks are now reversed."))
	return data[1:]

register_message({37: msg_reversedeck})

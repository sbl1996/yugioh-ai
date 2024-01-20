import io

from ygo.envs.card import Card

def msg_set(self, data):
	data = io.BytesIO(data[1:])
	code = self.read_u32(data)
	loc = self.read_u32(data)
	card = Card(code)
	card.set_location(loc)
	set(self, card)
	return data.read()

def set(self, card):
	c = card.controller
	cpl = self.players[c]
	opl = self.players[1 - c]
	cpl.notify(cpl._("You set %s (%s) in %s position.") %
	(card.get_spec(cpl), card.get_name(), card.get_position(cpl)))
	on = self.players[c].nickname
	opl.notify(opl._("%s sets %s in %s position.") %
	(on, card.get_spec(opl), card.get_position(opl)))

MESSAGES = {54: msg_set}



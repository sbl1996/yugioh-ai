from ygo.envs.glb import register_message
import io

from ygo.envs.card import Card
from ygo.constants import LOCATION, POSITION

def msg_pos_change(self, data):
	data = io.BytesIO(data[1:])
	code = self.read_u32(data)
	card = Card(code)
	card.controller = self.read_u8(data)
	card.location = LOCATION(self.read_u8(data))
	card.sequence = self.read_u8(data)
	prevpos = POSITION(self.read_u8(data))
	card.position = POSITION(self.read_u8(data))
	pos_change(self, card, prevpos)
	return data.read()

def pos_change(self, card, prevpos):
	if not self.verbose:
		return
	cpl = self.players[card.controller]
	op = self.players[1 - card.controller]
	cs = card.get_spec(cpl)
	cso = card.get_spec(op)
	cpl.notify(cpl._("The position of card %s (%s) was changed to %s.") % (cs, card.get_name(), card.get_position(cpl)))
	op.notify(op._("The position of card %s (%s) was changed to %s.") % (cso, card.get_name(), card.get_position(op)))

register_message({53: msg_pos_change})



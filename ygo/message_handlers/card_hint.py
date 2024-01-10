import io

from ygo.constants import AMOUNT_ATTRIBUTES, AMOUNT_RACES

def msg_card_hint(self, data):
	data = io.BytesIO(data[1:])
	loc = self.read_u32(data)
	pl, loc, seq, pos = self.unpack_location(loc)
	type = self.read_u8(data)
	value = self.read_u32(data)
	card = self.get_card(pl, loc, seq)
	if card:
		self.cm.call_callbacks('card_hint', card, type, value)
	return data.read()

def card_hint(self, card, type, value):
	if type == 3: # race announcement
		for pl in self.players:
			races = [pl.strings['system'][1020+i] for i in range(AMOUNT_RACES) if value & (1<<i)]
			pl.notify(pl._("{spec} ({name}) selected {value}.").format(spec=card.get_spec(pl), name=card.get_name(pl), value=', '.join(races)))
	elif type == 4: # attribute announcement
		for pl in self.players:
			attributes = [pl.strings['system'][1010+i] for i in range(AMOUNT_ATTRIBUTES) if value & (1<<i)]
			pl.notify(pl._("{spec} ({name}) selected {value}.").format(spec=card.get_spec(pl), name=card.get_name(pl), value=', '.join(attributes)))

	else:
		print("unhandled card hint type", type)
		print("hint value", value)

MESSAGES = {160: msg_card_hint}

CALLBACKS = {'card_hint': card_hint}

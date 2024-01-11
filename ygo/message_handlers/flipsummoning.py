import io

from ygo.constants import LOCATION
from ygo.duel import Duel


def msg_flipsummoning(duel: Duel, data):
	data = io.BytesIO(data[1:])
	code = duel.read_u32(data)
	location = duel.read_u32(data)
	c = location & 0xff
	loc = LOCATION((location >> 8) & 0xff)
	seq = (location >> 16) & 0xff
	card = duel.get_card(c, loc, seq)
	flipsummoning(duel, card)
	return data.read()

def flipsummoning(duel: Duel, card):
	cpl = duel.players[card.controller]
	for pl in duel.players:
		spec = card.get_spec(pl)
		pl.notify(pl._("{player} flip summons {card} ({spec}).")
		.format(player=cpl.nickname, card=card.get_name(pl), spec=spec))

MESSAGES = {64: msg_flipsummoning}

CALLBACKS = {'flipsummoning': flipsummoning}

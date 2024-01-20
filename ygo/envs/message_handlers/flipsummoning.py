from ygo.envs.glb import register_message
import io

from ygo.constants import LOCATION
from ygo.envs.duel import Duel


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
	if not duel.verbose:
		return
	cpl = duel.players[card.controller]
	for pl in duel.players:
		spec = card.get_spec(pl)
		pl.notify(pl._("{player} flip summons {card} ({spec}).")
		.format(player=cpl.nickname, card=card.get_name(), spec=spec))

register_message({64: msg_flipsummoning})



from ygo.envs.glb import register_message
from typing import List

import io

from ygo.envs.card import Card
from ygo.envs.duel import Duel


def msg_draw(duel: Duel, data):
	data = io.BytesIO(data[1:])
	player = duel.read_u8(data)
	drawed = duel.read_u8(data)
	cards = []
	for i in range(drawed):
		c = duel.read_u32(data)
		card = Card(c & 0x7fffffff)
		cards.append(card)
	draw(duel, player, cards)
	return data.read()


def draw(duel: Duel, player: int, cards: List[Card]):
	if not duel.verbose:
		return
	pl = duel.players[player]
	pl.notify(pl._("Drew %d cards:") % len(cards))
	for i, c in enumerate(cards):
		pl.notify("%d: %s" % (i+1, c.get_name()))
	op = duel.players[1 - player]
	op.notify(op._("Opponent drew %d cards.") % len(cards))


register_message({90: msg_draw})



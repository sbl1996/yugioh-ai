from ygo.envs.glb import register_message
import io

from ygo.constants import LOCATION
from ygo.envs.duel import Duel


def msg_confirm_cards(duel: Duel, data):
	data = io.BytesIO(data[1:])
	player = duel.read_u8(data)
	size = duel.read_u8(data)
	cards = []
	for i in range(size):
		code = duel.read_u32(data)
		c = duel.read_u8(data)
		l = LOCATION(duel.read_u8(data))
		s = duel.read_u8(data)
		card = duel.get_card(c, l, s)
		cards.append(card)
	confirm_cards(duel, player, cards)
	return data.read()


def confirm_cards(duel: Duel, player: int, cards):
	player = duel.players[cards[0].controller]
	op = duel.players[1 - cards[0].controller]
	players = [op]
	for pl in players:
		if duel.verbose:
			pl.notify(pl._("{player} shows you {count} cards.")
				.format(player=player.nickname, count=len(cards)))
		for i, c in enumerate(cards):
			if duel.verbose:
				pl.notify("%s: %s" % (i + 1, c.get_name()))
			duel.revealed[(c.controller, c.location, c.sequence)] = True

register_message({31: msg_confirm_cards})



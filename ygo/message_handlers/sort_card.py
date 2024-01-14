import io

from ygo.card import Card
from ygo.constants import LOCATION
from ygo.duel import Duel, Decision
from ygo.utils import parse_ints


def msg_sort_card(duel: Duel, data):
	data = io.BytesIO(data[1:])
	player = duel.read_u8(data)
	size = duel.read_u8(data)
	cards = []
	for i in range(size):
		card = Card(duel.read_u32(data))
		card.controller = duel.read_u8(data)
		card.location = LOCATION(duel.read_u8(data))
		card.sequence = duel.read_u8(data)
		cards.append(card)
	sort_card(duel, player, cards)
	return data.read()


def sort_card(duel: Duel, player: int, cards):
	pl = duel.players[player]
	def prompt():
		pl.notify(pl._("Sort %d cards by entering numbers separated by spaces (c = cancel):") % len(cards))
		for i, c in enumerate(cards):
			pl.notify("%d: %s" % (i+1, c.get_name(pl)))
		return pl.notify(Decision, r)
	def error(text):
		pl.notify(text)
		return prompt()
	def r(caller):
		if caller.text == 'c':
			duel.set_responseb(bytes([255]))
			return
		ints = [i - 1 for i in parse_ints(caller.text)]
		if len(ints) != len(cards):
			return error(pl._("Please enter %d values.") % len(cards))
		if len(ints) != len(set(ints)):
			return error(pl._("Duplicate values not allowed."))
		if any(i < 0 or i > len(cards) - 1 for i in ints):
			return error(pl._("Please enter values between 1 and %d.") % len(cards))
		duel.set_responseb(bytes([ints.index(c) for c in range(len(cards))]))
	prompt()

MESSAGES = {25: msg_sort_card}



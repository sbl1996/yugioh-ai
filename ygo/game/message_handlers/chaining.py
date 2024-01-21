import io

from ygo.game.card import Card
from ygo.constants import TYPE
from ygo.game.duel import Duel


def msg_chaining(duel: Duel, data):
	data = io.BytesIO(data[1:])
	code = duel.read_u32(data)
	card = Card(code)
	card.set_location(duel.read_u32(data))
	tc = duel.read_u8(data)
	tl = duel.read_u8(data)
	ts = duel.read_u8(data)
	desc = duel.read_u32(data)
	cs = duel.read_u8(data)
	chaining(duel, card, tc, tl, ts, desc, cs)
	return data.read()


def chaining(duel: Duel, card: Card, tc, tl, ts, desc, cs):
	c = card.controller
	o = 1 - c
	n = duel.players[c].nickname
	duel.chaining_player = c

	duel.players[c].notify(duel.players[c]._("Activating {0} ({1})").format(card.get_spec(duel.players[c]), card.get_name(duel.players[c])))
	duel.players[o].notify(duel.players[o]._("{0} activating {1} ({2})").format(n, card.get_spec(duel.players[o]), card.get_name(duel.players[o])))

MESSAGES = {70: msg_chaining}



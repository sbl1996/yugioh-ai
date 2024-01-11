import io

from ygo.card import Card
from ygo.constants import LOCATION
from ygo.duel import Duel


def msg_confirm_decktop(duel: Duel, data):
	cards = []
	data = io.BytesIO(data[1:])
	player = duel.read_u8(data)
	count = duel.read_u8(data)
	for i in range(count):
		code = duel.read_u32(data)
		if code & 0x80000000:
			code = code ^ 0x80000000 # don't know what this actually does
		card = Card(code)
		card.controller = duel.read_u8(data)
		card.location = LOCATION(duel.read_u8(data))
		card.sequence = duel.read_u8(data)
		cards.append(card)
	confirm_decktop(duel, player, cards)
	return data.read()


def msg_decktop(duel: Duel, data):
	data = io.BytesIO(data[1:])
	player = duel.read_u8(data)
	duel.read_u8(data) # don't know what this number does
	code = duel.read_u32(data)
	if code & 0x80000000:
		code = code ^ 0x80000000 # don't know what this actually does
	decktop(duel, player, Card(code))
	return data.read()


def decktop(duel: Duel, player: int, card: Card):
	player = duel.players[player]
	for pl in duel.players:
		if pl is player:
			pl.notify(pl._("you reveal your top deck card to be %s")%(card.get_name(pl)))
		else:
			pl.notify(pl._("%s reveals their top deck card to be %s")%(player.nickname, card.get_name(pl)))


def confirm_decktop(duel: Duel, player: int, cards):
	player = duel.players[player]
	for pl in duel.players:
		if pl is player:
			pl.notify(pl._("you reveal the following cards from your deck:"))
		else:
			pl.notify(pl._("%s reveals the following cards from their deck:")%(player.nickname))
		for i, c in enumerate(cards):
			pl.notify("%d: %s"%(i+1, c.get_name(pl)))

MESSAGES = {38: msg_decktop, 30: msg_confirm_decktop}
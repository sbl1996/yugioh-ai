import io

from ygo.card import Card
from ygo.constants import LOCATION


def msg_sort_chain(self, data):
	data = io.BytesIO(data[1:])
	player = self.read_u8(data)
	size = self.read_u8(data)
	cards = []
	for i in range(size):
		code = self.read_u32(data)
		card = Card(code)
		card.controller = self.read_u8(data)
		card.location = LOCATION(self.read_u8(data))
		card.sequence = self.read_u8(data)
		cards.append(card)
	sort_chain(self, player, cards)
	return data.read()


def sort_chain(self, player, cards):
	self.set_responsei(-1)


MESSAGES = {21: msg_sort_chain}

CALLBACKS = {'sort_chain': sort_chain}

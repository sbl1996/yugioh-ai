import io

from ygo import globals
from ygo.duel import ffi, lib, card_reader_callback, Duel, Decision


def msg_announce_card(duel: Duel, data):
	data = io.BytesIO(data[1:])
	player = duel.read_u8(data)
	size = duel.read_u8(data)
	options = []
	for i in range(size):
		options.append(duel.read_u32(data))
	announce_card(duel, player, options)
	return data.read()


def announce_card(duel: Duel, player: int, options):
	pl = duel.players[player]
	def prompt():
		pl.notify(pl._("Enter the name of a card:"))
		if len(options) == 3 and options[1] == 1073742082 and options[2] == 1073741831: # not is_type
			names = []
			for c in duel.unique_cards:
				if not (c.type & options[0]):
					names.append(c.name)
		else:
			raise Exception("Unknown options: %r" % options)
		return pl.notify(Decision, r, names, no_abort=pl._("Invalid command."))
	def error(text):
		pl.notify(text)
		return prompt()
	def r(caller):
		card = duel.get_card_by_name(pl, caller.text)
		if card is None:
			return error(pl._("No results found."))
		cd = ffi.new('struct card_data *')
		card_reader_callback(card.code, cd)
		if not lib.declarable(cd, len(options), options):
			return error(pl._("Wrong type."))
		duel.set_responsei(card.code)
	prompt()

MESSAGES = {142: msg_announce_card}



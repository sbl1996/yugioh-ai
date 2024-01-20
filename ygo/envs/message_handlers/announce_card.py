from ygo.envs.glb import register_message
import io

from ygo.constants import OPCODE
from ygo.envs.duel import ffi, lib, card_reader_callback, Duel, Decision
from ygo.envs import glb


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
		if len(options) == 3 and options[1] == OPCODE.ISTYPE and options[2] == OPCODE.NOT:
			names = []
			for c in duel.unique_cards:
				if not (c.type & options[0]):
					names.append(c.name)
		elif len(options) % 3 == 2 and options[1] == OPCODE.ISCODE:
			codes = [options[0]]
			if len(options) > 3:
				if not (set(options[3::3]) == {OPCODE.ISCODE} and set(options[4::3]) == {OPCODE.OR}):
					raise Exception("Unknown options: %r" % options)
				codes += options[2::3]
			names = []
			for code in codes:
				names.append(glb.get_card(code).name)
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

register_message({142: msg_announce_card})



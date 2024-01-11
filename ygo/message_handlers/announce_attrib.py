import io
import natsort

from ygo.duel import Duel, Decision
from ygo.constants import AMOUNT_ATTRIBUTES, ATTRIBUTES_OFFSET


def msg_announce_attrib(duel: Duel, data):
	data = io.BytesIO(data[1:])
	player = duel.read_u8(data)
	count = duel.read_u8(data)
	avail = duel.read_u32(data)
	announce_attrib(duel, player, count, avail)
	return data.read()


def announce_attrib(duel: Duel, player: int, count, avail):
	pl = duel.players[player]
	attrmap = {duel.strings['system'][ATTRIBUTES_OFFSET+i]: (1<<i) for i in range(AMOUNT_ATTRIBUTES)}
	avail_attributes = {k: v for k, v in attrmap.items() if avail & v}
	avail_attributes_keys = natsort.natsorted(list(avail_attributes.keys()))
	avail_attributes_values = [avail_attributes[r] for r in avail_attributes_keys]
	def prompt():
		pl.notify("Type %d attributes separated by spaces." % count)
		for i, attrib in enumerate(avail_attributes_keys):
			pl.notify("%d. %s" % (i + 1, attrib))
		pl.notify(Decision, r)
	def r(caller):
		items = caller.text.split()
		ints = []
		try:
			ints = [int(i) for i in items]
		except ValueError:
			pass
		ints = [i for i in ints if i > 0 <= len(avail_attributes_keys)]
		ints = set(ints)
		if len(ints) != count:
			pl.notify("Invalid attributes.")
			return prompt()
		value = sum(avail_attributes_values[i - 1] for i in ints)
		duel.set_responsei(value)
	return prompt()

MESSAGES = {141: msg_announce_attrib}

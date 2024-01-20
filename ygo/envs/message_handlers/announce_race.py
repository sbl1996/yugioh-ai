import io
import natsort

from ygo.constants import AMOUNT_RACES, RACES_OFFSET
from ygo.envs.duel import Duel, Decision


def msg_announce_race(duel: Duel, data):
	data = io.BytesIO(data[1:])
	player = duel.read_u8(data)
	count = duel.read_u8(data)
	avail = duel.read_u32(data)
	announce_race(duel, player, count, avail)
	return data.read()


def announce_race(duel: Duel, player: int, count, avail):
	pl = duel.players[player]
	racemap = {duel.strings['system'][RACES_OFFSET+i]: (1<<i) for i in range(AMOUNT_RACES)}
	avail_races = {k: v for k, v in racemap.items() if avail & v}
	avail_races_keys = natsort.natsorted(list(avail_races.keys()))
	def prompt():
		pl.notify("Type %d races separated by spaces." % count)
		for i, s in enumerate(avail_races_keys):
			pl.notify("%d: %s" % (i+1, s))
		pl.notify(Decision, r)
	def error(text):
		pl.notify(text)
		pl.notify(Decision, r)
	def r(caller):
		ints = []
		try:
			for i in caller.text.split():
				ints.append(int(i) - 1)
		except ValueError:
			return error("Invalid value.")
		if len(ints) != count:
			return error("%d items required." % count)
		if len(ints) != len(set(ints)):
			return error("Duplicate values not allowed.")
		if any(i > len(avail_races) - 1 or i < 0 for i in ints):
			return error("Invalid value.")
		result = 0
		for i in ints:
			result |= avail_races[avail_races_keys[i]]
		duel.set_responsei(result)
	prompt()

MESSAGES = {140: msg_announce_race}



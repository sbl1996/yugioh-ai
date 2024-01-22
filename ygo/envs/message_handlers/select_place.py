from ygo.envs.glb import register_message
import io

from ygo.envs.duel import Duel, ActionRequired


def msg_select_place(duel: Duel, data):
	data = io.BytesIO(data)
	msg = duel.read_u8(data)
	player = duel.read_u8(data)
	count = duel.read_u8(data)
	if count == 0: count = 1
	flag = duel.read_u32(data)
	options, r = select_place(duel, player, count, flag)
	return ActionRequired("select_place", player, options, r, data.read())


def select_place(duel: Duel, player: int, count, flag):
	pl = duel.players[player]
	specs = duel.flag_to_usable_cardspecs(flag)
	if duel.verbose:
		if count == 1:
			pl.notify(pl._("Select place for card, one of %s.") % ", ".join(specs))
		else:
			pl.notify(pl._("Select %d places for card, from %s.") % (count, ", ".join(specs)))

	def r(caller):
		values = caller.text.split()
		if len(set(values)) != len(values):
			raise ValueError("Duplicate values not allowed.")
		if len(values) != count:
			raise ValueError("Wrong number of values.")
		if any(value not in specs for value in values):
			raise ValueError("Invalid cardspec.")
		resp = b''
		for value in values:
			l, s = duel.cardspec_to_ls(value)
			if value.startswith('o'):
				plr = 1 - player
			else:
				plr = player
			resp += bytes([plr, l, s])
		duel.set_responseb(resp)
	return specs, r


register_message({18: msg_select_place, 24: msg_select_place})



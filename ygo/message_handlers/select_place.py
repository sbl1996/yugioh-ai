import io

from ygo.duel import Duel, Decision


def msg_select_place(duel: Duel, data):
	data = io.BytesIO(data)
	msg = duel.read_u8(data)
	player = duel.read_u8(data)
	count = duel.read_u8(data)
	if count == 0: count = 1
	flag = duel.read_u32(data)
	select_place(duel, player, count, flag)
	return data.read()


def select_place(duel: Duel, player: int, count, flag):
	pl = duel.players[player]
	specs = duel.flag_to_usable_cardspecs(flag)
	if count == 1:
		pl.notify(pl._("Select place for card, one of %s.") % ", ".join(specs))
	else:
		pl.notify(pl._("Select %d places for card, from %s.") % (count, ", ".join(specs)))

	def r(caller):
		values = caller.text.split()
		if len(set(values)) != len(values):
			pl.notify(pl._("Duplicate values not allowed."))
			return pl.notify(Decision, r, specs)
		if len(values) != count:
			pl.notify(pl._("Please enter %d values.") % count)
			return pl.notify(Decision, r, specs)
		if any(value not in specs for value in values):
			pl.notify(pl._("Invalid cardspec. Try again."))
			return pl.notify(Decision, r, specs)
		resp = b''
		for value in values:
			l, s = duel.cardspec_to_ls(value)
			if value.startswith('o'):
				plr = 1 - player
			else:
				plr = player
			resp += bytes([plr, l, s])
		duel.set_responseb(resp)

	pl.notify(Decision, r, specs)

MESSAGES = {18: msg_select_place, 24: msg_select_place}

CALLBACKS = {'select_place': select_place}

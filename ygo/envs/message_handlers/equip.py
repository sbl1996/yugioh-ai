import io

from ygo.envs.duel import Duel


def msg_equip(duel: Duel, data):
	data = io.BytesIO(data[1:])
	loc = duel.read_u32(data)
	target = duel.read_u32(data)
	u = duel.unpack_location(loc)
	card = duel.get_card(u[0], u[1], u[2])
	u = duel.unpack_location(target)
	target = duel.get_card(u[0], u[1], u[2])
	equip(duel, card, target)
	return data.read()

def equip(duel: Duel, card, target):
	for pl in duel.players:
		c = duel.cardlist_info_for_player(card, pl)
		t = duel.cardlist_info_for_player(target, pl)
		pl.notify(pl._("{card} equipped to {target}.")
			.format(card=c, target=t))

MESSAGES = {93: msg_equip}



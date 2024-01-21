import io

from ygo.constants import LOCATION, POSITION
from ygo.game.duel import Duel


def msg_become_target(duel: Duel, data):
	data = io.BytesIO(data[1:])
	u = duel.read_u8(data)
	target = duel.read_u32(data)
	tc = target & 0xff
	tl = LOCATION((target >> 8) & 0xff)
	tseq = (target >> 16) & 0xff
	tpos = POSITION((target >> 24) & 0xff)
	become_target(duel, tc, tl, tseq)
	return data.read()


def become_target(duel: Duel, tc, tl, tseq):
	card = duel.get_card(tc, tl, tseq)
	if not card:
		return
	name = duel.players[duel.chaining_player].nickname
	for pl in duel.players:
		spec = card.get_spec(pl)
		tcname = card.get_name(pl)
		if card.controller != pl.duel_player and card.position & POSITION.FACEDOWN:
			tcname = pl._("%s card") % card.get_position(pl)
		pl.notify(pl._("%s targets %s (%s)") % (name, spec, tcname))


MESSAGES = {83: msg_become_target}



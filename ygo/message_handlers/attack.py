import io

from ygo.constants import LOCATION, POSITION
from ygo.duel import Duel


def msg_attack(duel: Duel, data):
	data = io.BytesIO(data[1:])
	attacker = duel.read_u32(data)
	ac = attacker & 0xff
	al = LOCATION((attacker >> 8) & 0xff)
	aseq = (attacker >> 16) & 0xff
	apos = POSITION((attacker >> 24) & 0xff)
	target = duel.read_u32(data)
	tc = target & 0xff
	tl = LOCATION((target >> 8) & 0xff)
	tseq = (target >> 16) & 0xff
	tpos = POSITION((target >> 24) & 0xff)
	attack(duel, ac, al, aseq, apos, tc, tl, tseq, tpos)
	return data.read()


def attack(duel: Duel, ac, al, aseq, apos, tc, tl, tseq, tpos):
	acard = duel.get_card(ac, al, aseq)
	if not acard:
		return
	name = duel.players[ac].nickname
	if tc == 0 and tl == 0 and tseq == 0 and tpos == 0:
		for pl in duel.players:
			aspec = acard.get_spec(pl)
			pl.notify(pl._("%s prepares to attack with %s (%s)") % (name, aspec, acard.get_name(pl)))
		return
	tcard = duel.get_card(tc, tl, tseq)
	if not tcard:
		return
	for pl in duel.players:
		aspec = acard.get_spec(pl)
		tspec = tcard.get_spec(pl)
		tcname = tcard.get_name(pl)
		if tcard.controller != pl.duel_player and tcard.position & POSITION.FACEDOWN:
			tcname = pl._("%s card") % tcard.get_position(pl)
		pl.notify(pl._("%s prepares to attack %s (%s) with %s (%s)") % (name, tspec, tcname, aspec, acard.get_name(pl)))

MESSAGES = {110: msg_attack}



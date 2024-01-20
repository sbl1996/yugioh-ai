from ygo.envs.glb import register_message
import io

from ygo.constants import LOCATION, TYPE
from ygo.envs.duel import Duel

def msg_battle(duel: Duel, data):
	data = io.BytesIO(data[1:])
	attacker = duel.read_u32(data)
	aa = duel.read_u32(data)
	ad = duel.read_u32(data)
	bd0 = duel.read_u8(data)
	tloc = duel.read_u32(data)
	da = duel.read_u32(data)
	dd = duel.read_u32(data)
	bd1 = duel.read_u8(data)
	battle(duel, attacker, aa, ad, bd0, tloc, da, dd, bd1)
	return data.read()


def battle(duel: Duel, attacker, aa, ad, bd0, tloc, da, dd, bd1):
	if not duel.verbose:
		return
	loc = LOCATION((attacker >> 8) & 0xff)
	seq = (attacker >> 16) & 0xff
	c2 = attacker & 0xff
	card = duel.get_card(c2, loc, seq)
	tc = tloc & 0xff
	tl = LOCATION((tloc >> 8) & 0xff)
	tseq = (tloc >> 16) & 0xff
	if tloc:
		target = duel.get_card(tc, tl, tseq)
	else:
		target = None
	for pl in duel.players:
		if card.type & TYPE.LINK:
			attacker_points = "%d"%aa
		else:
			attacker_points = "%d/%d"%(aa, ad)

		if target:
			if target.type & TYPE.LINK:
				defender_points = "%d"%da
			else:
				defender_points = "%d/%d"%(da, dd)

		if target:
			pl.notify(pl._("%s (%s) attacks %s (%s)") % (card.get_name(), attacker_points, target.get_name(), defender_points))
		else:
			pl.notify(pl._("%s (%s) attacks") % (card.get_name(), attacker_points))

register_message({111: msg_battle})



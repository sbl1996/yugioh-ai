from ygo.envs.glb import register_message
import io

from ygo.envs.duel import Duel


def msg_lpupdate(duel: Duel, data):
	data = io.BytesIO(data[1:])
	player = duel.read_u8(data)
	lp = duel.read_u32(data)
	lpupdate(duel, player, lp)
	return data.read()

def lpupdate(duel: Duel, player, lp):
	if lp > duel.lp[player]:
		duel.recover(player, lp - duel.lp[player])
	else:
		duel.damage(player, duel.lp[player] - lp)

register_message({94: msg_lpupdate})



from ygo.envs.glb import register_message
import io
from ygo.envs.duel import Duel

def msg_chain_solved(duel: Duel, data):
	data = io.BytesIO(data[1:])
	count = duel.read_u8(data)
	chain_solved(duel, count)
	return data.read()

def chain_solved(duel: Duel, count):
	duel.revealed = {}

register_message({73: msg_chain_solved})



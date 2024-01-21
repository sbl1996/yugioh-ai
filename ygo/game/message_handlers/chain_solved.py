import io
from ygo.game.duel import Duel

def msg_chain_solved(duel: Duel, data):
	data = io.BytesIO(data[1:])
	count = duel.read_u8(data)
	chain_solved(duel, count)
	return data.read()

def chain_solved(duel: Duel, count):
	duel.revealed = {}

MESSAGES = {73: msg_chain_solved}



import io

from ygo.duel import Duel


def msg_win(duel: Duel, data):
	data = io.BytesIO(data[1:])
	player = duel.read_u8(data)
	reason = duel.read_u8(data)
	win(duel, player, reason)
	return data.read()


def win(duel: Duel, player, reason):
	winners = [duel.players[player]]
	losers = [duel.players[1 - player]]

	l_reason = duel.strings['victory'][reason]

	duel.winner = player
	duel.win_reason = l_reason

	for w in winners:
		w.notify(w._("You won (%s).") % l_reason)
	for l in losers:
		l.notify(l._("You lost (%s).") % l_reason)

	duel.end()

MESSAGES = {5: msg_win}



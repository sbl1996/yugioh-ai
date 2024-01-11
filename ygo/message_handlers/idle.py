import io

from ygo.duel import Duel


def msg_idlecmd(duel: Duel, data):
	duel.state = 'idle'
	data = io.BytesIO(data[1:])
	player = duel.read_u8(data)
	summonable = duel.read_cardlist(data)
	spsummon = duel.read_cardlist(data)
	repos = duel.read_cardlist(data)
	idle_mset = duel.read_cardlist(data)
	idle_set = duel.read_cardlist(data)
	idle_activate = duel.read_cardlist(data, True)
	to_bp = duel.read_u8(data)
	to_ep = duel.read_u8(data)
	cs = duel.read_u8(data)
	idle(duel, summonable, spsummon, repos, idle_mset, idle_set, idle_activate, to_bp, to_ep, cs)
	return data.read()


def idle(duel: Duel, summonable, spsummon, repos, idle_mset, idle_set, idle_activate, to_bp, to_ep, cs):
	duel.state = "idle"
	pl = duel.players[duel.tp]
	duel.summonable = summonable
	duel.spsummon = spsummon
	duel.repos = repos
	duel.idle_mset = idle_mset
	duel.idle_set = idle_set
	duel.idle_activate = idle_activate
	duel.to_bp = bool(to_bp)
	duel.to_ep = bool(to_ep)
	duel.idle_action(pl)

MESSAGES = {11: msg_idlecmd}

CALLBACKS = {'idle': idle}

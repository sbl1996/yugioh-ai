import io

from ygo.card import Card
from ygo.duel import Duel, Decision


def msg_select_chain(duel: Duel, data):
	data = io.BytesIO(data[1:])
	player = duel.read_u8(data)
	size = duel.read_u8(data)
	spe_count = duel.read_u8(data)
	forced = duel.read_u8(data)
	hint_timing = duel.read_u32(data)
	other_timing = duel.read_u32(data)
	chains = []
	for i in range(size):
		et = duel.read_u8(data)
		code = duel.read_u32(data)
		loc = duel.read_u32(data)
		card = Card(code)
		card.set_location(loc)
		desc = duel.read_u32(data)
		chains.append((et, card, desc))
	select_chain(duel, player, size, spe_count, forced, chains)
	return data.read()


def select_chain(duel: Duel, player: int, size, spe_count, forced, chains):
	if size == 0 and spe_count == 0:
		duel.keep_processing = True
		duel.set_responsei(-1)
		return
	pl = duel.players[player]
	duel.chaining_player = player
	op = duel.players[1 - player]
	if not op.seen_waiting:
		op.notify(op._("Waiting for opponent."))
		op.seen_waiting = True
	chain_cards = [c[1] for c in chains]
	specs = {}
	for i in range(len(chains)):
		card = chains[i][1]
		card.chain_index = i
		desc = chains[i][2]
		cs = card.get_spec(pl)
		chain_count = chain_cards.count(card)
		if chain_count > 1:
			cs += chr(ord('a')+list(specs.values()).count(card))
		specs[cs] = card
		card.chain_spec = cs
		card.effect_description = card.get_effect_description(pl, desc, True)

	def prompt():
		if forced:
			pl.notify(pl._("Select chain:"))
		else:
			pl.notify(pl._("Select chain (c to cancel):"))
		for card in chain_cards:
			if card.effect_description == '':
				pl.notify("%s: %s" % (card.chain_spec, card.get_name(pl)))
			else:
				pl.notify("%s (%s): %s"%(card.chain_spec, card.get_name(pl), card.effect_description))
		# if forced:
		# 	prompt = pl._("Select card to chain:")
		# else:
		# 	prompt = pl._("Select card to chain (c = cancel):")

		options = []
		if not forced:
			options.append('c')
		for spec in specs:
			options.append(spec)

		pl.notify(
			Decision,
			r,
			options,
		)

	def r(caller):
		if caller.text == 'c' and not forced:
			duel.set_responsei(-1)
			return
		if caller.text.startswith('i'):
			info = True
			caller.text = caller.text[1:]
		else:
			info = False
		if caller.text not in specs:
			pl.notify(pl._("Invalid spec."))
			return prompt()
		card = specs[caller.text]
		idx = card.chain_index
		if info:
			duel.show_info(card, pl)
			return prompt()
		duel.set_responsei(idx)
	prompt()

MESSAGES = {16: msg_select_chain}



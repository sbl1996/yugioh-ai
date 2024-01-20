from ygo.envs.glb import register_message
import io

from ygo.envs.card import Card
from ygo.constants import TYPE
from ygo.envs.duel import Duel


def msg_summoned(duel: Duel, data):
	return data[1:]


def msg_summoning(duel: Duel, data, special=False):
	data = io.BytesIO(data[1:])
	code = duel.read_u32(data)
	card = Card(code)
	card.set_location(duel.read_u32(data))
	summoning(duel, card, special=special)
	return data.read()


def summoning(duel: Duel, card, special=False):
	if not duel.verbose:
		return
	nick = duel.players[card.controller].nickname
	for pl in duel.players:
		pos = card.get_position(pl)
		if special:
			if card.type & TYPE.LINK:
				pl.notify(pl._("%s special summoning %s (%d) in %s position.") % (nick, card.get_name(), card.attack, pos))
			else:
				pl.notify(pl._("%s special summoning %s (%d/%d) in %s position.") % (nick, card.get_name(), card.attack, card.defense, pos))
		else:
			pl.notify(pl._("%s summoning %s (%d/%d) in %s position.") % (nick, card.get_name(), card.attack, card.defense, pos))


def msg_summoning_special(duel: Duel, *args, **kwargs):
	kwargs['special'] = True
	msg_summoning(duel, *args, **kwargs)


register_message({60: msg_summoning, 62: msg_summoning_special, 61: msg_summoned})



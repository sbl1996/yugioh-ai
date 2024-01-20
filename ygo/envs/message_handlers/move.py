from ygo.envs.glb import register_message
import io

from ygo.envs.card import Card
from ygo.constants import POSITION, REASON, LOCATION, TYPE, INFORM
import ygo.exceptions
from ygo.envs.duel import Duel


def msg_move(duel: Duel, data):
	data = io.BytesIO(data[1:])
	code = duel.read_u32(data)
	location = duel.read_u32(data)
	newloc = duel.read_u32(data)
	reason = REASON(duel.read_u32(data))
	move(duel, code, location, newloc, reason)
	return data.read()


def move(duel: Duel, code, location, newloc, reason):
	if not duel.verbose:
		return
	try:
		card = Card(code)
	except ygo.exceptions.CardNotFoundError:
		return
	card.set_location(location)
	cnew = Card(code)
	cnew.set_location(newloc)
	pl = duel.players[card.controller]
	op = duel.players[1 - card.controller]
	plspec = card.get_spec(pl)
	opspec = card.get_spec(op)
	plnewspec = cnew.get_spec(pl)
	opnewspec = cnew.get_spec(op)

	getspec = lambda p: plspec if p.duel_player == pl.duel_player else opspec
	getnewspec = lambda p: plnewspec if p.duel_player == pl.duel_player else opnewspec

	card_visible = True
	
	if card.position & POSITION.FACEDOWN and cnew.position & POSITION.FACEDOWN:
		card_visible = False

	getvisiblename = lambda p: card.get_name() if card_visible else p._("Face-down card")

	if reason & REASON.DESTROY and card.location != cnew.location:
		duel.inform(
			pl,
			(INFORM.PLAYER, lambda p: p._("Card %s (%s) destroyed.") % (plspec, card.get_name())),
			(INFORM.OPPONENT, lambda p: p._("Card %s (%s) destroyed.") % (opspec, card.get_name()))
		)
	elif card.location == cnew.location and card.location & LOCATION.ONFIELD:
		if card.controller != cnew.controller:
			# controller changed too (e.g. change of heart)
			duel.inform(
				pl,
				(INFORM.PLAYER, lambda p: p._("your card {spec} ({name}) changed controller to {op} and is now located at {targetspec}.").format(spec=plspec, name = card.get_name(), op = op.nickname, targetspec = plnewspec)),
				(INFORM.OPPONENT, lambda p: p._("you now control {plname}s card {spec} ({name}) and its located at {targetspec}.").format(plname=pl.nickname, spec=opspec, name = card.get_name(), targetspec = opnewspec)),
			)
		else:
			# only column changed (alien decks e.g.)
			duel.inform(
				pl,
				(INFORM.PLAYER, lambda p: p._("your card {spec} ({name}) switched its zone to {targetspec}.").format(spec=plspec, name=card.get_name(), targetspec=plnewspec)),
				(INFORM.OPPONENT, lambda p: p._("{plname}s card {spec} ({name}) changed its zone to {targetspec}.").format(plname=pl.nickname, spec=getspec(p), targetspec=getnewspec(p), name=card.get_name())),
			)
	elif reason & REASON.DISCARD and card.location != cnew.location:
		duel.inform(
			pl,
			(INFORM.PLAYER, lambda p: p._("you discarded {spec} ({name}).").format(spec = plspec, name = card.get_name())),
			(INFORM.OPPONENT, lambda p: p._("{plname} discarded {spec} ({name}).").format(plname=pl.nickname, spec=getspec(p), name=card.get_name())),
		)
	elif card.location == LOCATION.REMOVED and cnew.location & LOCATION.ONFIELD:
		duel.inform(
			pl,
			(INFORM.PLAYER, lambda p: p._("your banished card {spec} ({name}) returns to the field at {targetspec}.").format(spec=plspec, name=card.get_name(), targetspec=plnewspec)),
			(INFORM.OPPONENT, lambda p: p._("{plname}'s banished card {spec} ({name}) returned to their field at {targetspec}.").format(plname=pl.nickname, spec=getspec(p), targetspec=getnewspec(p), name=card.get_name())),
		)
	elif card.location == LOCATION.GRAVE and cnew.location & LOCATION.ONFIELD:
		duel.inform(
			pl,
			(INFORM.PLAYER, lambda p: p._("your card {spec} ({name}) returns from the graveyard to the field at {targetspec}.").format(spec=plspec, name=card.get_name(), targetspec=plnewspec)),
			(INFORM.OPPONENT, lambda p: p._("{plname}s card {spec} ({name}) returns from the graveyard to the field at {targetspec}.").format(plname = pl.nickname, spec=getspec(p), targetspec=getnewspec(p), name = card.get_name())),
		)
	elif cnew.location == LOCATION.HAND and card.location != cnew.location:
		duel.inform(
			pl,
			(INFORM.PLAYER, lambda p: p._("Card {spec} ({name}) returned to hand.").format(spec=plspec, name=card.get_name())),
		)
	elif reason & (REASON.RELEASE | REASON.SUMMON) and card.location != cnew.location:
		duel.inform(
			pl,
			(INFORM.PLAYER, lambda p: p._("You tribute {spec} ({name}).").format(spec=plspec, name=card.get_name())),
			(INFORM.OPPONENT, lambda p: p._("{plname} tributes {spec} ({name}).").format(plname=pl.nickname, spec=getspec(p), name=getvisiblename(p))),
		)
	elif card.location == LOCATION.OVERLAY | LOCATION.MZONE and cnew.location & LOCATION.GRAVE:
		duel.inform(
			pl,
			(INFORM.PLAYER, lambda p: p._("you detached %s.")%(card.get_name())),
			(INFORM.OPPONENT, lambda p: p._("%s detached %s")%(pl.nickname, card.get_name())),
		)
	elif card.location != cnew.location and cnew.location == LOCATION.GRAVE:
		duel.inform(
			pl,
			(INFORM.PLAYER, lambda p: p._("your card {spec} ({name}) was sent to the graveyard.").format(spec=plspec, name=card.get_name())),
			(INFORM.OPPONENT, lambda p: p._("{plname}'s card {spec} ({name}) was sent to the graveyard.").format(plname=pl.nickname, spec=getspec(p), name=card.get_name())),
		)
	elif card.location != cnew.location and cnew.location == LOCATION.REMOVED:
		duel.inform(
			pl,
			(INFORM.PLAYER, lambda p: p._("your card {spec} ({name}) was banished.").format(spec=plspec, name=card.get_name())),
			(INFORM.OPPONENT, lambda p: p._("{plname}'s card {spec} ({name}) was banished.").format(plname=pl.nickname, spec=getspec(p), name=getvisiblename(p))),
		)
	elif card.location != cnew.location and cnew.location == LOCATION.DECK:
		duel.inform(
			pl,
			(INFORM.PLAYER, lambda p: p._("your card {spec} ({name}) returned to your deck.").format(spec=plspec, name=card.get_name())),
			(INFORM.OPPONENT, lambda p: p._("{plname}'s card {spec} ({name}) returned to their deck.").format(plname=pl.nickname, spec=getspec(p), name=getvisiblename(p))),
		)
	elif card.location != cnew.location and cnew.location == LOCATION.EXTRA:
		duel.inform(
			pl,
			(INFORM.PLAYER, lambda p: p._("your card {spec} ({name}) returned to your extra deck.").format(spec=plspec, name=card.get_name())),
			(INFORM.OPPONENT, lambda p: p._("{plname}'s card {spec} ({name}) returned to their extra deck.").format(plname=pl.nickname, spec=getspec(p), name=card.get_name())),
		)
	elif card.location == LOCATION.DECK and cnew.location == LOCATION.SZONE and cnew.position != POSITION.FACEDOWN:
		def fn(p):
			if p is pl:
				return p._("Activating {0} ({1})").format(cnew.get_spec(p), cnew.get_name())
			else:
				return p._("{0} activating {1} ({2})").format(pl.nickname, cnew.get_spec(p), cnew.get_name())
				
		duel.inform(
			pl,
			(INFORM.ALL, fn)
		)

	elif cnew.location == (LOCATION.OVERLAY | LOCATION.MZONE):
		attached_to = duel.get_card(cnew.controller, cnew.location ^ LOCATION.OVERLAY, cnew.sequence)

		duel.inform(
			pl,
			(INFORM.PLAYER, lambda p: p._("your card {spec} ({name}) was attached to {targetspec} ({targetname}) as XYZ material").format(spec=getspec(p), name=card.get_name(), targetspec=attached_to.get_spec(p), targetname=attached_to.get_name())),
			(INFORM.OPPONENT, lambda p: p._("{plname}'s card {spec} ({name}) was attached to {targetspec} ({targetname}) as XYZ material").format(spec=getspec(p), name=card.get_name(), targetspec=attached_to.get_spec(p), targetname=attached_to.get_name(), plname=pl.nickname)),
		)

register_message({50: msg_move})



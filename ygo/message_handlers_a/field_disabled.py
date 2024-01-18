import io
from ygo.duel import Duel


def msg_field_disabled(duel: Duel, data):
	data = io.BytesIO(data[1:])
	locations = duel.read_u32(data)
	field_disabled(duel, locations)
	return data.read()

def field_disabled(duel: Duel, locations):
	specs = duel.flag_to_usable_cardspecs(locations, reverse=True)
	opspecs = []
	for spec in specs:
		if spec.startswith('o'):
			opspecs.append(spec[1:])
		else:
			opspecs.append('o'+spec)
	duel.players[0].notify(duel.players[0]._("Field locations %s are disabled.") % ", ".join(specs))
	duel.players[1].notify(duel.players[1]._("Field locations %s are disabled.") % ", ".join(opspecs))

MESSAGES = {56: msg_field_disabled}



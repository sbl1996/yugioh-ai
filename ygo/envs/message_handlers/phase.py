from ygo.envs.glb import register_message
import io

from ygo.constants import PHASES


def msg_new_phase(duel, data):
	data = io.BytesIO(data[1:])
	phase_ = duel.read_u16(data)
	phase(duel, phase_)
	return data.read()


def phase(duel, phase):
	duel.current_phase = phase
	if not duel.verbose:
		return
	phase_str = PHASES.get(phase, str(phase))
	for pl in duel.players:
		pl.notify(pl._('entering %s.') % pl._(phase_str))

register_message({41: msg_new_phase})


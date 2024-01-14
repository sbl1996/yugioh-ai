import io

from ygo.constants import PHASES


def msg_new_phase(self, data):
	data = io.BytesIO(data[1:])
	phase_ = self.read_u16(data)
	phase(self, phase_)
	return data.read()


def phase(self, phase):
	phase_str = PHASES.get(phase, str(phase))
	for pl in self.players:
		pl.notify(pl._('entering %s.') % pl._(phase_str))
	self.current_phase = phase

MESSAGES = {41: msg_new_phase}


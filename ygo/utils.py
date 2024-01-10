import collections
import os.path
import sys


try:
	from _duel import ffi, lib
	DUEL_AVAILABLE = True
except ImportError:
	DUEL_AVAILABLE = False


def process_duel(d):
	while d.started:
		res = d.process()
		if res & 0x20000:
			break
		elif res & 0x10000 and res != 0x10000:
			if d.keep_processing:
				d.keep_processing = False
				continue
			break


def process_duel_replay(duel):
	res = lib.process(duel.duel)
	l = lib.get_message(duel.duel, ffi.cast('byte *', duel.buf))
	data = ffi.unpack(duel.buf, l)
	cb = duel.cm.callbacks
	duel.cm.callbacks = collections.defaultdict(list)
	def tp(t):
		duel.tp = t
	duel.cm.register_callback('new_turn', tp)
	def recover(player, amount):
		duel.lp[player] += amount
	def damage(player, amount):
		duel.lp[player] -= amount
	def tag_swap(player):
		c = duel.players[player]
		n = duel.tag_players[player]
		duel.players[player] = n
		duel.watchers[player] = c
		duel.tag_players[player] = c
	duel.cm.register_callback('recover', recover)
	duel.cm.register_callback('damage', damage)
	duel.cm.register_callback('tag_swap', tag_swap)
	duel.process_messages(data)
	duel.cm.callbacks = cb
	return data

def check_sum(cards, acc):
	if acc < 0:
		return False
	if not cards:
		return acc == 0
	l1 = cards[0].param[0]
	l2 = cards[0].param[1]
	nc = cards[1:]
	res1 = check_sum(nc, acc - l1)
	if l2 > 0:
		res2 = check_sum(nc, acc - l2)
	else:
		res2 = False
	return res1 or res2

def parse_ints(text):
	ints = []
	try:
		for i in text.split():
			ints.append(int(i))
	except ValueError:
		pass
	return ints

def get_root_directory():
	return os.path.dirname(os.path.abspath(sys.argv[0]))



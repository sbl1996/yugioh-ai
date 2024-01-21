import itertools
import os.path


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
	return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_deck(fn):
    with open(fn) as f:
        lines = f.readlines()
        noside = itertools.takewhile(lambda x: "side" not in x, lines)
        deck = [int(line) for line in  noside if line[:-1].isdigit()]
        return deck
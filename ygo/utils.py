import itertools
from pathlib import Path

from envpool2.ygopro import init_module


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
	cur = Path(__file__).resolve()
	return str(cur.parent.parent)


def load_deck(fn):
    with open(fn) as f:
        lines = f.readlines()
        noside = itertools.takewhile(lambda x: "side" not in x, lines)
        deck = [int(line) for line in  noside if line[:-1].isdigit()]
        return deck


def extract_deck_name(path):
	return Path(path).stem

_languages = {
    "english": "en",
    "chinese": "zh",
}

def init_ygopro(lang, deck, code_list_file, preload_tokens=True):
	short = _languages[lang]
	db_path = Path(get_root_directory(), 'locale', short, 'cards.cdb')
	deck_fp = Path(deck)
	if deck_fp.is_dir():
		decks = {f.stem: str(f) for f in deck_fp.glob("*.ydk")}
		deck_dir = deck_fp
		deck_name = 'random'
	else:
		deck_name = Path(deck).stem
		decks = {deck_name: deck}
		deck_dir = Path(deck).parent
	if preload_tokens:
		token_deck = deck_dir / "_tokens.ydk"
		if not token_deck.exists():
			raise FileNotFoundError(f"Token deck not found: {token_deck}")
		decks["_tokens"] = str(token_deck)
	init_module(str(db_path), code_list_file, decks)
	return deck_name
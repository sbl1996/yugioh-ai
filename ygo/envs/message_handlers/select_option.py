import io

from ygo.envs.card import Card
from ygo.envs.duel import Duel, Decision
from ygo.utils import parse_ints


def msg_select_option(duel: Duel, data):
    data = io.BytesIO(data[1:])
    player = duel.read_u8(data)
    size = duel.read_u8(data)
    options = []
    for i in range(size):
        options.append(duel.read_u32(data))
    select_option(duel, player, options)
    return data.read()


def select_option(duel: Duel, player: int, options):
    pl = duel.players[player]

    card = None
    opts = []
    for opt in options:
        if opt > 10000:
            code = opt >> 4
            card = Card(code)
            string = card.get_strings()[opt & 0xf]
        else:
            string = pl._("Unknown option %d" % opt)
            string = duel.strings['system'].get(opt, string)
        opts.append(string)

    def prompt():
        pl.notify(pl._("Select option:"))
        valid = [str(i + 1) for i in range(len(opts))]
        for i, opt in enumerate(opts):
            pl.notify("%d: %s" % (i + 1, opt))
        pl.notify(Decision, r, valid)

    def error(text):
        pl.notify(text)
        return prompt()

    def r(caller):
        idx = parse_ints(caller.text)
        if not idx or len(idx) != 1 or idx[0] - 1 >= len(options):
            return error(pl._("Invalid option."))
        idx = idx[0] - 1
        string = opts[idx]
        for p in duel.players:
            if p is pl:
                p.notify(p._("You selected option {0}: {1}").format(idx + 1, string))
            else:
                p.notify(p._("{0} selected option {1}: {2}").format(pl.nickname, idx + 1, string))
        duel.set_responsei(idx)

    prompt()

MESSAGES = {14: msg_select_option}



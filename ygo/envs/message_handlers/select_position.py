import io

from ygo.envs.card import Card
from ygo.constants import POSITION
from ygo.envs.duel import Duel, Decision
from ygo.utils import parse_ints


def msg_select_position(duel: Duel, data):
    data = io.BytesIO(data[1:])
    player = duel.read_u8(data)
    code = duel.read_u32(data)
    card = Card(code)
    positions = POSITION(duel.read_u8(data))
    select_position(duel, player, card, positions)
    return data.read()


def select_position(duel: Duel, player: int, card, positions):
    pl = duel.players[player]
    menus = [
        (POSITION.FACEUP_ATTACK, "Face-up attack", 1),
        (POSITION.FACEDOWN_ATTACK, "Face-down attack", 2),
        (POSITION.FACEUP_DEFENSE, "Face-up defense", 4),
        (POSITION.FACEDOWN_DEFENSE, "Face-down defense", 8),
    ]
    valid_positions = []
    for i, (pos, name, resp) in enumerate(menus):
        if positions & pos:
            valid_positions.append(i)

    def prompt():
        pl.notify(pl._("Select position for %s:") % (card.get_name(),))
        options = []
        for i, pi in enumerate(valid_positions):
            name = menus[pi][1]
            options.append(str(i + 1))
            pl.notify("%d: %s" % (i + 1, name))
        pl.notify(Decision, r, options)

    def error(text):
        pl.notify(text)
        return prompt()

    def r(caller):
        p = parse_ints(caller.text)
        if not p or len(p) != 1 or p[0] - 1 >= len(valid_positions):
            return error(pl._("Invalid position."))
        p = p[0] - 1
        resp = menus[valid_positions[p]][2]
        duel.set_responsei(resp)

    prompt()


MESSAGES = {19: msg_select_position}



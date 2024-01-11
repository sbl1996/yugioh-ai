import io

from ygo.card import Card
from ygo.duel import Duel, Decision


def msg_select_unselect_card(duel: Duel, data):
    data = io.BytesIO(data[1:])
    player = duel.read_u8(data)
    finishable = duel.read_u8(data)
    cancelable = duel.read_u8(data)
    min = duel.read_u8(data)
    max = duel.read_u8(data)
    select_size = duel.read_u8(data)
    select_cards = []
    for i in range(select_size):
        code = duel.read_u32(data)
        loc = duel.read_u32(data)
        card = Card(code)
        card.set_location(loc)
        select_cards.append(card)
    unselect_size = duel.read_u8(data)
    unselect_cards = []
    for i in range(unselect_size):
        code = duel.read_u32(data)
        loc = duel.read_u32(data)
        card = Card(code)
        card.set_location(loc)
        unselect_cards.append(card)
    select_unselect_card(duel, player, finishable, cancelable, min, max, select_cards, unselect_cards)
    return data.read()

def select_unselect_card(duel: Duel, player: int, finishable, cancelable, min, max, select_cards, unselect_cards):
    pl = duel.players[player]
    pl.card_list = select_cards + unselect_cards

    def prompt():
        text = pl._("Check or uncheck %d to %d cards by entering their number")%(min, max)
        if cancelable and not finishable:
            text += "\n" + pl._("Enter c to cancel")
        if finishable:
            text += "\n" + pl._("Enter f to finish")
        pl.notify(text)

    for i, c in enumerate(pl.card_list):
        name = duel.cardlist_info_for_player(c, pl)
        if c in select_cards:
            state = pl._("unchecked")
        else:
            state = pl._("checked")
        pl.notify("%d: %s (%s)" % (i+1, name, state))

    def error(text):
        pl.notify(text)
        return prompt()

    def f(caller):
        if caller.text == 'c' and (cancelable and not finishable) or caller.text == 'f' and finishable:
            duel.set_responsei(-1)
            return
        try:
            c = int(caller.text, 10)
        except ValueError:
            return error(pl._("Invalid command"))
        if c < 1 or c > len(pl.card_list):
            return error(pl._("Number not in range"))
        buf = bytes([1, c - 1])
        duel.set_responseb(buf)

    options = []
    if cancelable and not finishable:
        options.append('c')
    if finishable:
        options.append('f')
    for i in range(1, len(pl.card_list) + 1):
        options.append(str(i))        

    pl.notify(Decision, f, options)

    return prompt()


MESSAGES = {26: msg_select_unselect_card}



import io
import struct
from twisted.internet import reactor

from ygo.card import Card
from ygo.constants import LOCATION
from ygo.duel_reader import DuelReader
from ygo.parsers.duel_parser import DuelParser
from ygo.utils import parse_ints, process_duel

def msg_select_counter(self, data):
    data = io.BytesIO(data[1:])
    player = self.read_u8(data)
    countertype = self.read_u16(data)
    count = self.read_u16(data)
    size = self.read_u8(data)
    cards = []
    for i in range(size):
        card = Card(self.read_u32(data))
        card.controller = self.read_u8(data)
        card.location = LOCATION(self.read_u8(data))
        card.sequence = self.read_u8(data)
        card.counter = self.read_u16(data)
        cards.append(card)
    self.cm.call_callbacks('select_counter', player, countertype, count, cards)
    return data.read()


def find_combinations(cards, expected_value, current_sum=0, current_combination=None, combinations_found=None):
    if current_combination is None:
        current_combination = []
    if combinations_found is None:
        combinations_found = []

    # If the current sum is equal to the expected value, add the current combination to the list of found combinations
    if current_sum == expected_value:
        combinations_found.append(current_combination.copy())
        return combinations_found

    # If the current sum is greater than the expected value, or there are no more cards to check, return
    if current_sum > expected_value or not cards:
        return []

    # Try all possible numbers for the current card
    for number in range(1, cards[0] + 1):
        # Add the number to the current combination and the current sum
        current_combination.append(number)
        current_sum += number

        # Recursively call the function for the remaining cards
        find_combinations(cards[1:], expected_value, current_sum, current_combination, combinations_found)

        # Remove the number from the current combination and the current sum
        current_combination.pop()
        current_sum -= number

    # Pad 0 to the end of the list of found combinations if there are not enough combinations
    combinations_found = [
        tuple(combination) + (0,) * (len(cards) - len(combination))
        for combination in combinations_found
    ]

    # Return the list of found combinations
    return combinations_found


def select_counter(self, player, countertype, count, cards):
    pl = self.players[player]
    counter_str = pl.strings['counter'][countertype]
    def prompt():
        pl.notify(pl._("Type new {counter} for {cards} cards, separated by spaces.")
            .format(counter=counter_str, cards=len(cards)))
        for c in cards:
            pl.notify("%s (%d)" % (c.get_name(pl), c.counter))
        counters = [c.counter for c in cards]
        options = [ " ".join([str(x) for x in comb]) for comb in find_combinations(counters, count) ]
        pl.notify(DuelReader, r, options, no_abort="Invalid command", restore_parser=DuelParser)
    def error(text):
        pl.notify(text)
        return prompt()
    def r(caller):
        ints = parse_ints(caller.text)
        ints = [i & 0xffff for i in ints]
        if len(ints) != len(cards):
            return error(pl._("Please specify %d values.") % len(cards))
        if any(cards[i].counter < val for i, val in enumerate(ints)):
            return error(pl._("Values cannot be greater than counter."))
        if sum(ints) != count:
            return error(pl._("Please specify %d values with a sum of %d.") % (len(cards), count))
        bytes = struct.pack('h' * len(cards), *ints)
        self.set_responseb(bytes)
        reactor.callLater(0, process_duel, self)
    prompt()

MESSAGES = {22: msg_select_counter}

CALLBACKS = {'select_counter': select_counter}

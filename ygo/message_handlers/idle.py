import io

from ygo.duel import Duel, Decision, Player
from ygo.constants import LOCATION, POSITION


def msg_idlecmd(duel: Duel, data):
	duel.state = 'idle'
	data = io.BytesIO(data[1:])
	player = duel.read_u8(data)
	summonable = duel.read_cardlist(data)
	spsummon = duel.read_cardlist(data)
	repos = duel.read_cardlist(data)
	idle_mset = duel.read_cardlist(data)
	idle_set = duel.read_cardlist(data)
	idle_activate = duel.read_cardlist(data, True)
	to_bp = duel.read_u8(data)
	to_ep = duel.read_u8(data)
	cs = duel.read_u8(data)
	idle(duel, summonable, spsummon, repos, idle_mset, idle_set, idle_activate, to_bp, to_ep, cs)
	return data.read()


def act_on_card(duel: Duel, caller, card):
    pl = duel.players[duel.tp]
    name = card.get_name(pl)
    if card in duel.idle_activate:
        card = duel.idle_activate[duel.idle_activate.index(card)]

    def prompt():
        options = []
        pl.notify(name)
        activate_count = duel.idle_activate.count(card)
        if card in duel.summonable:
            options.append("s")
            pl.notify("s: " + pl._("Summon this card in face-up attack position."))
        if card in duel.idle_set:
            options.append("t")
            pl.notify("t: " + pl._("Set this card."))
        if card in duel.idle_mset:
            options.append("m")
            pl.notify("m: " + pl._("Summon this card in face-down defense position."))
        if card in duel.repos:
            options.append("r")
            pl.notify("r: " + pl._("reposition this card."))
        if card in duel.spsummon:
            options.append("c")
            pl.notify("c: " + pl._("Special summon this card."))
        if activate_count > 0:
            effect_descriptions = []
            for i in range(activate_count):
                ind = duel.idle_activate[duel.idle_activate.index(card) + i].data
                effect_descriptions.append(card.get_effect_description(pl, ind))

            if activate_count == 1:
                options.append("v")
                pl.notify("v: " + effect_descriptions[0])
            else:
                for i in range(activate_count):
                    options.append("v" + chr(97 + i))
                    pl.notify("v" + chr(97 + i) + ": " + effect_descriptions[i])
        pl.notify("i: " + pl._("Show card info."))
        pl.notify("z: " + pl._("back."))
        pl.notify(
            Decision,
            action,
            options,
        )

    def error(text):
        pl.notify(text)
        return prompt()

    def action(caller):
        if caller.text == "s" and card in duel.summonable:
            duel.set_responsei(duel.summonable.index(card) << 16)
        elif caller.text == "t" and card in duel.idle_set:
            duel.set_responsei((duel.idle_set.index(card) << 16) + 4)
        elif caller.text == "m" and card in duel.idle_mset:
            duel.set_responsei((duel.idle_mset.index(card) << 16) + 3)
        elif caller.text == "r" and card in duel.repos:
            duel.set_responsei((duel.repos.index(card) << 16) + 2)
        elif caller.text == "c" and card in duel.spsummon:
            duel.set_responsei((duel.spsummon.index(card) << 16) + 1)
        elif caller.text == "i":
            duel.show_info(card, pl)
            return prompt()
        elif caller.text == "z":
            return idle_action(duel, pl)
        elif caller.text.startswith("v"):
            activate_count = duel.idle_activate.count(card)
            if (
                len(caller.text) > 2
                or activate_count == 0
                or (len(caller.text) == 1 and activate_count > 1)
                or (len(caller.text) == 2 and activate_count == 1)
            ):
                return error(pl._("Invalid action."))

            index = duel.idle_activate.index(card)
            if len(caller.text) == 2:
                # parse the second letter
                try:
                    o = ord(caller.text[1])
                except TypeError:
                    o = -1
                ad = o - ord("a")
                if not (0 <= ad <= 25) or ad >= activate_count:
                    return error(pl._("Invalid action."))
                index += ad
            duel.set_responsei((index << 16) + 5)
        else:
            return error(pl._("Invalid action."))
    prompt()


def idle_action(duel: Duel, pl: Player):
    def prompt():
        options = duel.get_usable(pl)
        pl.notify(pl._("Select a card on which to perform an action."))
        pl.notify(
            pl._(
                "h shows your hand, tab and tab2 shows your or the opponent's table, ? shows usable cards."
            )
        )
        if duel.to_bp:
            options.append("b")
            pl.notify(pl._("b: Enter the battle phase."))
        if duel.to_ep:
            # always go to bp if possible
            if not duel.to_bp:
                options.append("e")
            pl.notify(pl._("e: End phase."))
        pl.notify(
            Decision,
            r,
            options,
        )

    # cards = []
    # for i in (0, 1):
    #     for j in (
    #         LOCATION.HAND,
    #         LOCATION.MZONE,
    #         LOCATION.SZONE,
    #         LOCATION.GRAVE,
    #         LOCATION.EXTRA,
    #     ):
    #         cards.extend(duel.get_cards_in_location(i, j))
    # specs = set(card.get_spec(duel.players[duel.tp]) for card in cards)

    def r(caller):
        if caller.text == "b" and duel.to_bp:
            duel.set_responsei(6)
            return
        elif caller.text == "e" and duel.to_ep:
            duel.set_responsei(7)
            return
        elif caller.text == "?":
            duel.show_usable(pl)
            return pl.notify(
                Decision,
                r,
            )
        elif caller.text in ["h", "hand"]:
            duel.show_cards_in_location(pl, pl.duel_player, LOCATION.HAND, hide_facedown=False)
            return prompt()
        elif caller.text == 'hand2':
            duel.show_cards_in_location(pl, 1 - pl.duel_player, LOCATION.HAND, hide_facedown=True)
            return prompt()
        elif caller.text == 'tab':
            pl.notify(pl._("Your table:"))
            duel.show_table(pl, pl.duel_player, hide_facedown=False)
            return prompt()
        elif caller.text == 'tab2':
            pl.notify(pl._("Opponent's table:"))
            duel.show_table(pl, 1 - pl.duel_player, hide_facedown=True)   
            return prompt()

        # Expensive, cost 2/3 of the execution time
        # if caller.text not in specs:
        #     pl.notify(pl._("Invalid specifier. Retry."))
        #     prompt()
        #     return
        loc, seq = duel.cardspec_to_ls(caller.text)

        if caller.text.startswith("o"):
            plr = 1 - duel.tp
        else:
            plr = duel.tp
        card = duel.get_card(plr, loc, seq)
        if not card:
            pl.notify(pl._("There is no card in that position."))
            prompt()
            return
        if plr == 1 - duel.tp:
            if card.position & POSITION.FACEDOWN:
                pl.notify(pl._("Face-down card."))
                return prompt()
        act_on_card(duel, caller, card)

    prompt()


def idle(duel: Duel, summonable, spsummon, repos, idle_mset, idle_set, idle_activate, to_bp, to_ep, cs):
	duel.state = "idle"
	pl = duel.players[duel.tp]
	duel.summonable = summonable
	duel.spsummon = spsummon
	duel.repos = repos
	duel.idle_mset = idle_mset
	duel.idle_set = idle_set
	duel.idle_activate = idle_activate
	duel.to_bp = bool(to_bp)
	duel.to_ep = bool(to_ep)
	idle_action(duel, pl)


MESSAGES = {11: msg_idlecmd}



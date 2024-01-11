from ygo.constants import *
from ygo.duel import Duel, Decision, Player


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
                no_abort=pl._("Invalid specifier. Retry."),
                prompt=pl._("Select a card:"),
            )
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
        duel.act_on_card(caller, card)

    prompt()


METHODS = {"idle_action": idle_action}

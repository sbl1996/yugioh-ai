from ygo.duel import Duel, Decision, Player


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
            return
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

METHODS = {"act_on_card": act_on_card}

from ygo.envs.glb import register_message
import io

from ygo.envs.duel import Duel, ActionRequired, Player
from ygo.constants import POSITION


def msg_idlecmd(duel: Duel, data):
    duel.state = 'idle'
    data = io.BytesIO(data[1:])
    player = duel.read_u8(data)
    duel.summonable = duel.read_cardlist(data)
    duel.spsummon = duel.read_cardlist(data)
    duel.repos = duel.read_cardlist(data)
    duel.idle_mset = duel.read_cardlist(data)
    duel.idle_set = duel.read_cardlist(data)
    duel.idle_activate = duel.read_cardlist(data, True)
    duel.to_bp = bool(duel.read_u8(data))
    duel.to_ep = bool(duel.read_u8(data))
    cs = duel.read_u8(data)

    assert duel.tp == player
    pl = duel.players[duel.tp]
    options, r = idle_action(duel, pl)
    return ActionRequired("idle_action", duel.tp, options, r, data.read())


def idle_action(duel: Duel, pl: Player):
    def prompt():
        options = []
        if duel.verbose:
            pl.notify(pl._("Select a card and action to perform."))

        for cards, cmd, desc in [
            (duel.summonable, "s", "Summon %s in face-up attack position."),
            (duel.idle_set, "t", "Set %s."),
            (duel.idle_mset, "m", "Summon %s in face-down defense position."),
            (duel.repos, "r", "Reposition %s."),
            (duel.spsummon, "c", "Special summon %s."),
        ]:
            for card in cards:
                spec = card.get_spec(pl)
                options.append(spec + " " + cmd)
                if duel.verbose:
                    pl.notify(spec + " " + cmd + ": " + pl._(desc % card.name))
        for card in duel.idle_activate:
            activate_count = duel.idle_activate.count(card)
            if activate_count > 1:
                raise NotImplementedError("Activate more than one effect.")
            spec = card.get_spec(pl)
            options.append(spec + " v")
            if duel.verbose:
                ind = duel.idle_activate[0].data
                effect_description = card.get_effect_description(pl, ind)
                pl.notify(spec + " v" + ": " + effect_description)

        if duel.to_bp:
            options.append("b")
            if duel.verbose:
                pl.notify(pl._("b: Enter the battle phase."))
        if duel.to_ep:
            # always go to bp if possible
            if not duel.to_bp:
                options.append("e")
                if duel.verbose:
                    pl.notify(pl._("e: End phase."))
        return options, r


    def r(caller):
        if caller.text == "b" and duel.to_bp:
            duel.set_responsei(6)
            return
        elif caller.text == "e" and duel.to_ep:
            duel.set_responsei(7)
            return
        spec, act = caller.text.split(" ")
        loc, seq = duel.cardspec_to_ls(spec)

        if spec.startswith("o"):
            plr = 1 - duel.tp
        else:
            plr = duel.tp
        card = duel.get_card(plr, loc, seq)
        if not card:
            raise ValueError("Invalid card: " + spec)
        if plr == 1 - duel.tp:
            if card.position & POSITION.FACEDOWN:
                raise ValueError("Cannot select opponent's face-down card.")

        if act == "s" and card in duel.summonable:
            duel.set_responsei(duel.summonable.index(card) << 16)
        elif act == "t" and card in duel.idle_set:
            duel.set_responsei((duel.idle_set.index(card) << 16) + 4)
        elif act == "m" and card in duel.idle_mset:
            duel.set_responsei((duel.idle_mset.index(card) << 16) + 3)
        elif act == "r" and card in duel.repos:
            duel.set_responsei((duel.repos.index(card) << 16) + 2)
        elif act == "c" and card in duel.spsummon:
            duel.set_responsei((duel.spsummon.index(card) << 16) + 1)
        elif act.startswith("v"):
            activate_count = duel.idle_activate.count(card)
            if activate_count > 1:
                raise NotImplementedError("Activate more than one effect.")
            index = duel.idle_activate.index(card)
            duel.set_responsei((index << 16) + 5)
        else:
            raise ValueError("Invalid action: " + act)

    return prompt()


register_message({11: msg_idlecmd})

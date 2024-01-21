from typing import List, Union, Optional
from dataclasses import dataclass

import sqlite3

import pandas as pd

from ygo.constants import TYPE, LOCATION, all_types, type2str, attribute2str, race2str, location2str, POSITION, position2str
from ygo.game.duel import Duel, Card as DuelCard, lib


def parse_types(value):
    types = []
    for t in all_types:
        if value & t:
            types.append(type2str[t])
    return types


def parse_attribute(value):
    attribute = attribute2str.get(value, None)
    assert attribute, "Invalid attribute, value: " + str(value)
    return attribute


def parse_race(value):
    race = race2str.get(value, None)
    assert race, "Invalid race, value: " + str(value)
    return race


def parse_position(value):
    position = position2str.get(value, None)
    assert position, "Invalid position, value: " + str(value)
    return position


@dataclass
class Card:
    id: int
    name: str
    desc: str
    types: List[str]

    position: Optional[str]
    spec: Optional[str]
    equip_target: Optional[str]

    @classmethod
    def from_duel(cls, card: DuelCard):
        if card.type & TYPE.MONSTER:
            return MonsterCard.from_duel(card)
        elif card.type & TYPE.SPELL:
            return SpellCard.from_duel(card)
        elif card.type & TYPE.TRAP:
            return TrapCard.from_duel(card)
        else:
            raise ValueError("Invalid card type: " + str(card.type))

@dataclass
class MonsterCard(Card):
    atk: int
    def_: int
    level: int
    race: str
    attribute: str

    @classmethod
    def from_duel(cls, card: DuelCard):
        id = card.code
        name = card.name
        desc = card.desc.replace("\r\n", "\\n")
        
        types = parse_types(int(card.type))
        
        atk = int(card.attack)
        def_ = int(card.defense)
        level = int(card.level)

        race = parse_race(int(card.race))
        attribute = parse_attribute(int(card.attribute))

        position = parse_position(int(card.position))
        spec = card.get_spec(card.controller)

        if card.equip_target:
            et = card.equip_target
            equip_target = et.get_spec(et.controller)
        else:
            equip_target = None
        return MonsterCard(
            id=id, name=name, desc=desc, types=types,
            atk=atk, def_=def_, level=level, race=race,
            attribute=attribute, position=position,
            spec=spec, equip_target=equip_target)


@dataclass
class SpellCard(Card):
    
    @classmethod
    def from_duel(cls, card: DuelCard):
        id = card.code
        name = card.name
        desc = card.desc.replace("\r\n", "\\n")
        
        types = parse_types(int(card.type))
        position = parse_position(int(card.position))
        spec = card.get_spec(card.controller)

        if card.equip_target:
            et = card.equip_target
            equip_target = et.get_spec(et.controller)
        else:
            equip_target = None
        return SpellCard(
            id=id, name=name, desc=desc, types=types,
            position=position, spec=spec, equip_target=equip_target
        )

@dataclass
class TrapCard(Card):

    @classmethod
    def from_duel(cls, card: DuelCard):
        id = card.code
        name = card.name
        desc = card.desc
        
        types = parse_types(int(card.type))
        position = parse_position(int(card.position))
        spec = card.get_spec(card.controller)

        if card.equip_target:
            et = card.equip_target
            equip_target = et.get_spec(et.controller)
        else:
            equip_target = None
        return TrapCard(
            id=id, name=name, desc=desc, types=types,
            position=position, spec=spec, equip_target=equip_target
        )


def spec_to_location(spec: str):
    if spec is None:
        return None
    if spec.isdigit():
        return LOCATION.DECK
    if spec.startswith("h"):
        return LOCATION.HAND
    elif spec.startswith("m"):
        return LOCATION.MZONE
    elif spec.startswith("s"):
        return LOCATION.SZONE
    elif spec.startswith("g"):
        return LOCATION.GRAVE
    elif spec.startswith("x"):
        return LOCATION.EXTRA
    elif spec.startswith("r"):
        return LOCATION.REMOVED
    else:
        raise ValueError("Invalid spec: " + spec)


def format_monster_card(card: MonsterCard, opponent=False):
    name = card.name
    typ = "/".join(card.types)

    attribute = card.attribute
    race = card.race

    level = str(card.level)

    atk = str(card.atk)
    if atk == '-2':
        atk = '?'

    def_ = str(card.def_)
    if def_ == '-2':
        def_ = '?'

    if typ == 'Monster/Normal':
        desc = "-"
    else:
        desc = card.desc

    spec = card.spec
    location = spec_to_location(spec)
    if not opponent:
        if location in [LOCATION.DECK, LOCATION.EXTRA, LOCATION.HAND, LOCATION.GRAVE, LOCATION.REMOVED]:
            if location == LOCATION.DECK:
                spec = "?"
            columns = [spec, name, typ, attribute, race, level, atk, def_, desc]
        elif location == LOCATION.MZONE:
            position = card.position
            columns = [spec, position, name, typ, attribute, race, level, atk, def_, desc]
        else:
            raise ValueError("Invalid zone for monster card: " + location2str[location])
        return " | ".join(columns)
    else:
        if location in [LOCATION.DECK, LOCATION.EXTRA, LOCATION.HAND]:
            return None
        elif location in [LOCATION.GRAVE, LOCATION.REMOVED]:
            spec = "o" + spec
            columns = [spec, name, typ, attribute, race, level, atk, def_, desc]
            return " | ".join(columns)
        elif location in [LOCATION.MZONE]:
            position = card.position
            spec = "o" + spec
            if position == position2str[POSITION.FACEDOWN_DEFENSE]:
                columns = [spec, position, "?", "?", "?", "?", "?", "?", "?", "?"]
            else:
                columns = [spec, position, name, typ, attribute, race, level, atk, def_, desc]
            return " | ".join(columns)
        else:
            raise ValueError("Invalid zone for monster card: " + location2str[location])


def format_spell_trap_card(card: Union[SpellCard, TrapCard], opponent=False):
    name = card.name
    typ = "/".join(card.types)
    desc = card.desc

    spec = card.spec
    location = spec_to_location(spec)
    if not opponent:
        if location in [LOCATION.DECK, LOCATION.HAND, LOCATION.GRAVE, LOCATION.REMOVED]:
            if location == LOCATION.DECK:
                spec = "?"
            columns = [spec, name, typ, "-", "-", "-", "-", "-", desc]
            return " | ".join(columns)
        elif location == LOCATION.SZONE:
            position = card.position
            equip_target = card.equip_target
            if equip_target is None:
                equip_target = "-"
            columns = [spec, position, name, typ, desc, equip_target]
            return " | ".join(columns)
        elif location == LOCATION.FZONE:
            position = card.position
            columns = [spec, position, name, typ, desc]
            return " | ".join(columns)
        else:
            card_type = "spell" if isinstance(card, SpellCard) else "trap"
            raise ValueError(f"Invalid zone for {card_type} card: " + location2str[location])
    else:
        if location in [LOCATION.DECK, LOCATION.HAND]:
            return None
        elif location in [LOCATION.GRAVE, LOCATION.REMOVED]:
            spec = "o" + spec
            columns = [spec, name, typ, "-", "-", "-", "-", "-", desc]
            return " | ".join(columns)
        elif location == LOCATION.SZONE:
            spec = "o" + spec
            position = card.position
            if position == position2str[POSITION.FACEDOWN]:
                columns = [spec, position, "?", "?", "?", "?"]
            else:
                equip_target = card.equip_target
                if equip_target is None:
                    equip_target = "-"
                columns = [spec, position, name, typ, desc, equip_target]
            return " | ".join(columns)
        elif location == LOCATION.FZONE:
            spec = "o" + spec
            position = card.position
            if position == position2str[POSITION.FACEDOWN]:
                columns = [spec, position, "?", "?", "?"]
            else:
                columns = [spec, position, name, typ, desc]
            return " | ".join(columns)
        else:
            card_type = "spell" if isinstance(card, SpellCard) else "trap"
            raise ValueError(f"Invalid zone for {card_type} card: " + location2str[location])


def format_card(card: Card, opponent=False):
    if isinstance(card, MonsterCard):
        return format_monster_card(card, opponent)
    elif isinstance(card, (SpellCard, TrapCard)):
        return format_spell_trap_card(card, opponent)
    else:
        raise ValueError("Invalid card type: " + str(card))


def show_duel_state(duel: Duel, player: int, opponent=False):
    if not opponent:
        print("# You\n")
    else:
        print("# Opponent\n")

    print("## LP")
    print(duel.lp[player])
    print("")

    deck_columns = ["Spec", "Name", "Type", "Attribute", "Race", "Level", "ATK", "DEF", "Description"]
    extra_deck_columns = deck_columns
    hand_columns = deck_columns
    main_monster_zone_columns = deck_columns[:1] + ["Position"] + deck_columns[1:]
    spell_trap_zone_columns = ["Spec", "Position", "Name", "Type", "Description", "Target"]
    field_zone_columns = spell_trap_zone_columns[:-1]
    graveyard_columns = deck_columns
    banished_columns = deck_columns
    for name, location, columns, hide_for_opponent in [
        ("Deck", LOCATION.DECK, deck_columns, True),
        ("Extra Deck", LOCATION.EXTRA, extra_deck_columns, True),
        ("Hand", LOCATION.HAND, hand_columns, True),
        ("Main Monster Zone", LOCATION.MZONE, main_monster_zone_columns, False),
        ("Spell & Trap Zone", LOCATION.SZONE, spell_trap_zone_columns, False),
        # ("Field Zone", LOCATION.FZONE, field_zone_columns, False),
        ("Graveyard (GY)", LOCATION.GRAVE, graveyard_columns, False),
        ("Banished (Remove from Play)", LOCATION.REMOVED, banished_columns, False),
    ]:
        print("## " + name)
        if opponent and hide_for_opponent:
            n_cards = lib.query_field_count(duel.duel, player, location)
            if n_cards == 0:
                print("Empty")
            else:
                print(f"{n_cards} cards")
        else:
            deck_cards = [
                Card.from_duel(card) for card in duel.get_cards_in_location(player, location)
            ]
            if len(deck_cards) == 0:
                print("Empty")
            else:
                print(" | ".join(columns))
                seps = ["---"] * len(columns)
                print(" | ".join(seps))

                for card in deck_cards:
                    print(format_card(card, opponent))
        print("")
    print("")


## For analyzing cards.db

def parse_monster_card(data) -> MonsterCard:
    id = int(data['id'])
    name = data['name']
    desc = data['desc']
    
    types = parse_types(int(data['type']))
    
    atk = int(data['atk'])
    def_ = int(data['def'])
    level = int(data['level'])

    if level >= 16:
        # pendulum monster
        level = level % 16

    race = parse_race(int(data['race']))
    attribute = parse_attribute(int(data['attribute']))
    return MonsterCard(id, name, desc, types, atk, def_, level, race, attribute)


def parse_spell_card(data) -> SpellCard:
    id = int(data['id'])
    name = data['name']
    desc = data['desc']
    
    types = parse_types(int(data['type']))
    return SpellCard(id, name, desc, types)


def parse_trap_card(data) -> TrapCard:
    id = int(data['id'])
    name = data['name']
    desc = data['desc']
    
    types = parse_types(int(data['type']))
    return TrapCard(id, name, desc, types)


def parse_card(data) -> Card:
    type_ = data['type']
    if type_ & TYPE.MONSTER:
        return parse_monster_card(data)
    elif type_ & TYPE.SPELL:
        return parse_spell_card(data)
    elif type_ & TYPE.TRAP:
        return parse_trap_card(data)
    else:
        raise ValueError("Invalid card type: " + str(type_))


def read_cards(cards_path, parse=False):
    conn = sqlite3.connect(cards_path)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM datas")
    datas_rows = cursor.fetchall()
    datas_columns = [description[0] for description in cursor.description]
    datas_df = pd.DataFrame(datas_rows, columns=datas_columns)

    cursor.execute("SELECT * FROM texts")
    texts_rows = cursor.fetchall()
    texts_columns = [description[0] for description in cursor.description]
    texts_df = pd.DataFrame(texts_rows, columns=texts_columns)

    cursor.close()
    conn.close()

    texts_df = texts_df.loc[:, ['id', 'name', 'desc']]
    merged_df = pd.merge(texts_df, datas_df, on='id')
    return merged_df


def parse_cards_from_db(cards_path):
    merged_df = read_cards(cards_path)
    cards_data = merged_df.to_dict('records')
    return [parse_card(data) for data in cards_data]

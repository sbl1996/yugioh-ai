try:
    from _duel import ffi, lib
    DUEL_AVAILABLE = True
except ImportError as exc:
    print(exc)
    DUEL_AVAILABLE = False

from typing import List

import os
import io
import struct
import random
import re

import natsort

from ygo.envs.card import Card
from ygo.constants import TYPE, LOCATION, POSITION, QUERY, INFORM
from ygo.envs import glb


class Decision:
    pass


class ActionRequired:

    def __init__(self, msg, player, options, callback, data):
        self.msg = msg
        self.player = player
        self.options = options
        self.callback = callback
        self.data = data


class Player:

    def __init__(self, cards, nickname, init_lp, verbose=True):
        # immutable
        self.cards = cards
        self.nickname = nickname
        self.init_lp = init_lp
        self.verbose = verbose

        # change for each duel
        self.duel_player = None

        # change during duel
        self.seen_waiting = False
        self.card_list = []     

    def init_state(self):
        self.duel_player = None
        self.seen_waiting = False
        self.card_list = []     

    _ = lambda self, t: t

    def notify(self, arg1, *args, **kwargs):
        pass


if DUEL_AVAILABLE:
    @ffi.def_extern()
    def card_reader_callback(code, data):
        cd = data[0]
        row = glb.db.database.execute('select * from datas where id=?', (code,)).fetchone()
        if row is None:
            print("Card %d not found in database" % code)
            raise RuntimeError
        cd.code = code
        cd.alias = row['alias']
        cd.setcode = row['setcode']
        cd.type = row['type']
        cd.level = row['level'] & 0xff
        cd.lscale = (row['level'] >> 24) & 0xff
        cd.rscale = (row['level'] >> 16) & 0xff
        cd.attack = row['atk']
        cd.defense = row['def']
        if cd.type & TYPE.LINK:
            cd.link_marker = cd.defense
            cd.defense = 0
        else:
            cd.link_marker = 0
        cd.race = row['race']
        cd.attribute = row['attribute']
        return 0

    lib.set_card_reader(lib.card_reader_callback)

    scriptbuf = ffi.new('char[131072]')
    @ffi.def_extern()
    def script_reader_callback(name, lenptr):
        fn = ffi.string(name)
        if not os.path.exists(fn):
            lenptr[0] = 0
            return ffi.NULL
        s = open(fn, 'rb').read()
        buf = ffi.buffer(scriptbuf)
        buf[0:len(s)] = s
        lenptr[0] = len(s)
        return ffi.cast('byte *', scriptbuf)

    lib.set_script_reader(lib.script_reader_callback)


class Duel:
    def __init__(self, seed=None, verbose=False, np_random=None):
        self.buf = ffi.new('char[]', 4096)
        self._np_random = np_random
        if seed is None:
            if np_random is None:
                seed = random.randint(0, 0xffffffff)
            else:
                seed = np_random.integers(0, 0xffffffff)
        self.seed = seed
        self.duel = lib.create_duel(seed)
        self.keep_processing = False
        self.to_ep = False
        self.to_m2 = False
        self.current_phase = 0
        self.players: List[Player] = [None, None]
        self.lp = [8000, 8000]
        self.started = False
        self.state = ''
        self.revealed = {}
        self.revealing = [False, False]
        self.cards = [None, None]
        self.unique_cards = None
        self.verbose = verbose

    def build_unique_cards(self):
        unique_code2cards = {}
        for cs in self.cards:
            for c in cs:
                if c.code not in unique_code2cards:
                    unique_code2cards[c.code] = c
        self.unique_cards = list(unique_code2cards.values())
        self.unique_code2cards = unique_code2cards

    def set_player(self, i, player: Player, shuffle=True):
        assert self.players[i] is None
        self.lp[i] = player.init_lp
        lib.set_player_info(self.duel, i, player.init_lp, 5, 1)
        player.duel_player = i
        player.verbose = self.verbose
        self.players[i] = player
        cards = self.load_deck(player, shuffle)
        self.cards[i] = cards

    def init(self, players, shuffle=True):
        for i, player in enumerate(players):
            self.set_player(i, player, shuffle)
            player.duel = self
        self.build_unique_cards()
        self.env_start()

    def load_deck(self, player, shuffle = True):
        full_deck = player.cards[:]
        c = []
        fusion = []
        xyz = []
        synchro = []
        link = []

        cards = []

        for tc in full_deck[::-1]:
            cc = Card(tc)
            if cc.extra:
                if cc.type & TYPE.FUSION:
                    fusion.append([tc, cc.level])
                if cc.type & TYPE.XYZ:
                    xyz.append([tc, cc.level])
                if cc.type & TYPE.SYNCHRO:
                    synchro.append([tc, cc.level])
                if cc.type & TYPE.LINK:
                    link.append([tc, cc.level])
            else:
                c.append(tc)
            cards.append(cc)

        if shuffle is True:
            if self._np_random is None:
                random.shuffle(c)
            else:
                self._np_random.shuffle(c)

        conv = lambda lvl: lvl[1]
        fusion.sort(key=conv, reverse=True)
        xyz.sort(key=conv, reverse=True)
        synchro.sort(key=conv, reverse=True)
        link.sort(key=conv, reverse=True)

        for tc in fusion:
            c.append(tc[0])
        for tc in xyz:
            c.append(tc[0])
        for tc in synchro:
            c.append(tc[0])
        for tc in link:
            c.append(tc[0])

        for sc in c[::-1]:
            lib.new_card(self.duel, sc, player.duel_player, player.duel_player, LOCATION.DECK.value, 0, POSITION.FACEDOWN_DEFENSE.value)
        return cards

    def env_start(self, rules = 5):
        # rules = 1, Traditional
        # rules = 0, Default
        # rules = 4, Link
        # rules = 5, MR5
        options = 0
        options = ((rules & 0xFF) << 16) + (options & 0xFFFF)
        lib.start_duel(self.duel, options)
        self.started = True

    
    def lib_process(self):
        res = lib.process(self.duel)
        l = lib.get_message(self.duel, ffi.cast('byte *', self.buf))
        data = ffi.unpack(self.buf, l)
        return res, data

    def end(self):
        lib.end_duel(self.duel)
        self.started = False
        for pl in self.players:
            pl.init_state()
        self.duel = None

    def read_cardlist(self, data, extra=False, extra8=False):
        res = []
        size = self.read_u8(data)
        for i in range(size):
            code = self.read_u32(data)
            controller = self.read_u8(data)
            location = LOCATION(self.read_u8(data))
            sequence = self.read_u8(data)
            card = self.get_card(controller, location, sequence)
            if extra:
                if extra8:
                    card.data = self.read_u8(data)
                else:
                    card.data = self.read_u32(data)
            res.append(card)
        return res

    def read_u8(self, buf):
        return struct.unpack('b', buf.read(1))[0]

    def read_u16(self, buf):
        return struct.unpack('h', buf.read(2))[0]

    def read_u32(self, buf):
        return struct.unpack('I', buf.read(4))[0]

    def set_responsei(self, r):
        lib.set_responsei(self.duel, r)

    def set_responseb(self, r):
        buf = ffi.new('char[64]', r)
        lib.set_responseb(self.duel, ffi.cast('byte *', buf))

    def get_cards_in_location(self, player, location) -> List[Card]:
        cards = []
        # flags = QUERY.CODE | QUERY.POSITION | QUERY.LEVEL | QUERY.RANK | QUERY.ATTACK | QUERY.DEFENSE | QUERY.EQUIP_CARD | QUERY.OVERLAY_CARD | QUERY.COUNTERS | QUERY.LSCALE | QUERY.RSCALE | QUERY.LINK
        flags = 14893875
        bl = lib.query_field_card(self.duel, player, location.value, flags, ffi.cast('byte *', self.buf), 0)
        buf = io.BytesIO(ffi.unpack(self.buf, bl))
        while True:
            if buf.tell() == bl:
                break
            length = self.read_u32(buf)
            if length == 4:
                continue #No card here
            f = self.read_u32(buf)
            code = self.read_u32(buf)
            card = Card(code)
            position = self.read_u32(buf)
            card.set_location(position)
            level = self.read_u32(buf)
            if (level & 0xff) > 0:
                card.level = level & 0xff
            rank = self.read_u32(buf)
            if (rank & 0xff) > 0:
                card.level = rank & 0xff
            card.attack = self.read_u32(buf)
            card.defense = self.read_u32(buf)

            card.equip_target = None

            if f & QUERY.EQUIP_CARD: # optional

                equip_target = self.read_u32(buf)
                pl = equip_target & 0xff
                loc = LOCATION((equip_target >> 8) & 0xff)
                seq = (equip_target >> 16) & 0xff
                card.equip_target = self.get_card(pl, loc, seq)

            card.xyz_materials = []

            xyz = self.read_u32(buf)

            for i in range(xyz):
                card.xyz_materials.append(Card(self.read_u32(buf)))

            cs = self.read_u32(buf)
            card.counters = []
            for i in range(cs):
                card.counters.append(self.read_u32(buf))

            card.lscale = self.read_u32(buf)
            card.rscale = self.read_u32(buf)

            link = self.read_u32(buf)
            link_marker = self.read_u32(buf)

            if (link & 0xff) > 0:
                card.level = link & 0xff

            if link_marker > 0:
                card.defense = link_marker

            cards.append(card)
        return cards

    def get_card(self, player, loc, seq) -> Card:
        flags = QUERY.CODE | QUERY.ATTACK | QUERY.DEFENSE | QUERY.POSITION | QUERY.LEVEL | QUERY.RANK | QUERY.LSCALE | QUERY.RSCALE | QUERY.LINK
        bl = lib.query_card(self.duel, player, loc.value, seq, flags.value, ffi.cast('byte *', self.buf), False)
        if bl == 0:
            return
        buf = io.BytesIO(ffi.unpack(self.buf, bl))
        f = self.read_u32(buf)
        if f == 4:
            return
        f = self.read_u32(buf)
        code = self.read_u32(buf)
        card = Card(code)
        position = self.read_u32(buf)
        card.set_location(position)
        level = self.read_u32(buf)
        if (level & 0xff) > 0:
            card.level = level & 0xff
        rank = self.read_u32(buf)
        if (rank & 0xff) > 0:
            card.level = rank & 0xff
        card.attack = self.read_u32(buf)
        card.defense = self.read_u32(buf)
        card.lscale = self.read_u32(buf)
        card.rscale = self.read_u32(buf)
        link = self.read_u32(buf)
        link_marker = self.read_u32(buf)
        if (link & 0xff) > 0:
            card.level = link & 0xff
        if link_marker > 0:
            card.defense = link_marker
        return card

    def get_card_by_name(self, pl, name):
        r = re.compile(r'^(\d+)\.(.+)$')
        r = r.search(name)
        if r:
            n, name = int(r.group(1)), r.group(2)
        else:
            n = 1
        if n == 0:
            n = 1
        name = '%'+name+'%'
        rows = glb.db.database.execute('select id from texts where name like ? limit ?', (name, n)).fetchall()
        if not rows:
            return
        nr = rows[min(n - 1, len(rows) - 1)]
        card = Card(nr[0])
        return card

    def unpack_location(self, loc):
        controller = loc & 0xff
        location = LOCATION((loc >> 8) & 0xff)
        sequence = (loc >> 16) & 0xff
        position = POSITION((loc >> 24) & 0xff)
        return (controller, location, sequence, position)

    def get_usable(self, pl):
        summonable = [card.get_spec(pl) for card in self.summonable]
        spsummon = [card.get_spec(pl) for card in self.spsummon]
        repos = [card.get_spec(pl) for card in self.repos]
        mset = [card.get_spec(pl) for card in self.idle_mset]
        idle_set = [card.get_spec(pl) for card in self.idle_set]
        idle_activate = [card.get_spec(pl) for card in self.idle_activate]
        return natsort.natsorted(set(summonable + spsummon + repos + mset + idle_set + idle_activate))

    def cardspec_to_ls(self, text):
        if text.startswith('o'):
            text = text[1:]
        r = re.search(r'^([a-z]+)(\d+)', text)
        if not r:
            return (None, None)
        if r.group(1) == 'h':
            l = LOCATION.HAND
        elif r.group(1) == 'm':
            l = LOCATION.MZONE
        elif r.group(1) == 's':
            l = LOCATION.SZONE
        elif r.group(1) == 'g':
            l = LOCATION.GRAVE
        elif r.group(1) == 'x':
            l = LOCATION.EXTRA
        elif r.group(1) == 'r':
            l = LOCATION.REMOVED
        else:
            return None, None
        return l, int(r.group(2)) - 1

    def flag_to_usable_cardspecs(self, flag, reverse=False):
        pm = flag & 0xff
        ps = (flag >> 8) & 0xff
        om = (flag >> 16) & 0xff
        os = (flag >> 24) & 0xff
        zone_names = ('m', 's', 'om', 'os')
        specs = []
        for zn, val in zip(zone_names, (pm, ps, om, os)):
            for i in range(8):
                if reverse:
                    avail = val & (1 << i) != 0
                else:
                    avail = val & (1 << i) == 0
                if avail:
                    specs.append(zn + str(i + 1))
        return specs

    def cardlist_info_for_player(self, card, pl):
        spec = card.get_spec(pl)
        if card.location == LOCATION.DECK:
            spec = pl._("deck")
        cls = (card.controller, card.location, card.sequence)
        if card.controller != pl.duel_player and card.position & POSITION.FACEDOWN and cls not in self.revealed:
            position = card.get_position(pl)
            return (pl._("{position} card ({spec})")
                .format(position=position, spec=spec))
        name = card.get_name()
        return "{name} ({spec})".format(name=name, spec=spec)

    @property
    def strings(self):
        return glb.strings.get_strings(glb.strings.primary_language)

    def inform(self, ref_player, *inf):
        """
        informs specific players in a duel
        players can be configured with constants from INFORM enum in constants
        each message consists of a callable which takes the player and returns the properly formatted text
        if no callable is received, the message is skipped
        a player cannot be informed twice through this method.
        
        example:
        duel.inform(pl, (INFORM.ALL, lambda p: p._("you were informed")))
        """

        if not ref_player or ref_player not in self.players:
            raise ValueError("reference player must be duelling in this duel")
            
        players = self.players[:]
        all = players

        informed = {}

        for t in inf:
            key = t[0]
            value = t[1]
            if not isinstance(key, INFORM):
                raise TypeError("inform key must be of type INFORM")

            if not callable(value):
                continue
            
            to_be_informed = list(filter(lambda p: \
                p not in informed and (\
                    (key & INFORM.PLAYER and p is ref_player) or \
                    (key & INFORM.OPPONENT and p is not ref_player and p in players)
                ), all))

            for p in to_be_informed:
                informed[p] = value

        for pl, cl in informed.items():
            pl.notify(cl(pl))

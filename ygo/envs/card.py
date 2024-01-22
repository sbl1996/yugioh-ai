from ygo.constants import TYPE, LOCATION, POSITION, AMOUNT_ATTRIBUTES, AMOUNT_RACES, ATTRIBUTES_OFFSET, RACES_OFFSET, LINK_MARKERS

from ygo.envs import glb

class Card(object):

	def __init__(self, code):

		row = glb.db.get_card(code)
		self.data = 0 # additional data fetched in certain cases (see Duel.read_cardlist)
		self.code = code
		self.alias = row['alias']
		self.setcode = row['setcode']
		self.type = TYPE(row['type'])
		self.level = row['level'] & 0xff
		self.lscale = (row['level'] >> 24) & 0xff
		self.rscale = (row['level'] >> 16) & 0xff
		self.attack = row['atk']
		self.defense = row['def']
		self.race = row['race']
		self.attribute = row['attribute']
		self.category = row['category']
		row = glb.db.get_text(code)
		self.name = row[1]
		self.desc = row[2]
		self.strings = []
		for i in range(3, len(row), 1):
			self.strings.append(row[i])

	def set_location(self, location):
		self.controller = location & 0xff
		self.location = LOCATION((location >> 8) & 0xff)
		self.sequence = (location >> 16) & 0xff
		self.position = POSITION((location >> 24) & 0xff)

	def __eq__(self, other):
		return self.code == other.code and self.location == other.location and self.sequence == other.sequence

	def get_name(self):
		return self.name

	def get_desc(self):
		return self.desc

	def get_strings(self):
		return self.strings

	def get_effect_description(self, pl, i, existing=False):
		s = ''
		e = False
		if i > 10000:
			code = i >> 4
		else:
			code = self.code

		row = glb.db.get_text(code)
		lstr = []
		for j in range(3, len(row), 1):
			lstr.append(row[j])

		try:
			if i == 0 or lstr[i-code*16].strip() == '':
				s = pl._("Activate this card.")
			else:
				s = lstr[i-code*16].strip()
				e = True
		except IndexError:
			s = glb.strings.get_string('system').get(i, '')
			if s != '':
				e = True

		if existing and not e:
			s = ''

		return s

	def get_info(self, pl):

		lst = []
		types = []
		t = str(self.type.value)
		for i in range(len(TYPE)):
			if self.type & (1 << i):
				types.append(glb.strings.get_string('system')[1050+i])
		for i in range(AMOUNT_ATTRIBUTES):
			if self.attribute & (1 << i):
				types.append(glb.strings.get_string('system')[ATTRIBUTES_OFFSET+i])
		for i in range(AMOUNT_RACES):
			if self.race & (1 << i):
				types.append(glb.strings.get_string('system')[RACES_OFFSET+i])

		lst.append("%s (%s)" % (self.get_name(), ", ".join(types)))
		if self.type & TYPE.MONSTER:
			if self.type & TYPE.LINK:
				lst.append(pl._("Attack: %d Link rating: %d")%(self.attack, self.level))
			elif self.type & TYPE.XYZ:
				lst.append(pl._("Attack: %d Defense: %d Rank: %d") % (self.attack, self.defense, self.level))
			else:
				lst.append(pl._("Attack: %d Defense: %d Level: %d") % (self.attack, self.defense, self.level))
		if self.type & TYPE.PENDULUM:
			lst.append(pl._("Pendulum scale: %d/%d") % (self.lscale, self.rscale))
		elif self.type & TYPE.LINK:
			lst.append(pl._("Link Markers: %s")%(self.get_link_markers(pl)))

		lst.append(pl._("Set: {set}").format(set = self.get_set(pl)))

		lst.append(self.get_desc())

		try:

			if self.type & TYPE.XYZ and self.location == LOCATION.MZONE:

				if len(self.xyz_materials):

					lst.append(pl._("attached xyz materials:"))

					for i in range(len(self.xyz_materials)):
						lst.append(str(i+1)+": "+self.xyz_materials[i].get_name())

				else:

					lst.append(pl._("no xyz materials attached"))

		except AttributeError:
			pass

		return "\n".join(lst)

	def get_position(self, pl):

		if self.position == POSITION.FACEUP_ATTACK:
			return pl._("face-up attack")
		elif self.position == POSITION.FACEDOWN_ATTACK:
			return pl._("face-down attack")
		elif self.position == POSITION.FACEUP_DEFENSE:
			if self.location & LOCATION.EXTRA:
				return pl._("face-up")
			return pl._("face-up defense")
		elif self.position == POSITION.FACEUP:
			return pl._("face-up")
		elif self.position == POSITION.FACEDOWN_DEFENSE:
			if self.location & LOCATION.EXTRA:
				return pl._("face down")
			return pl._("face-down defense")
		elif self.position == POSITION.FACEDOWN:
			return pl._("face down")

	def get_spec(self, pl):
		if isinstance(pl, int):
			player = pl
		else:
			player = pl.duel_player
		s = ""
		if self.controller != player:
			s += "o"
		if self.location == LOCATION.HAND:
			s += "h"
		elif self.location == LOCATION.MZONE:
			s += "m"
		elif self.location == LOCATION.SZONE:
			s += "s"
		elif self.location == LOCATION.GRAVE:
			s += "g"
		elif self.location == LOCATION.EXTRA:
			s += "x"
		elif self.location == LOCATION.REMOVED:
			s += "r"
		s += str(self.sequence + 1)
		return s

	def get_link_markers(self, pl):

		lst = []

		for m in LINK_MARKERS.keys():
			if self.defense & m:
				lst.append(pl._(LINK_MARKERS[m]))

		return ', '.join(lst)

	def get_set(self, pl):

		def _get_text(i):
			try:
				text = glb.strings.get_string('setname').get(i, '')

				if not text:
					return pl._('unknown')
				return text
			except KeyError:
				return pl._('unknown')
		
		if not self.setcode:
			return pl._("no set")
		
		set1 = self.setcode & 0xffff
		set2 = (self.setcode & 0xffff0000) >> 16

		desc = []
		
		if set:
			if set1 & 0xff:
				desc.append(_get_text(set1 & 0xff))
			if set1 & 0xff00:
				desc.append(_get_text(set1))

		if set2:
			if set2 & 0xff:
				desc.append(_get_text(set2 & 0xff))
			if set2 & 0xff00:
				desc.append(_get_text(set2))

		return ', '.join(desc)

	@property
	def extra(self):
		return bool(self.type & TYPE.EXTRA)

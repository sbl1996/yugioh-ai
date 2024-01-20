import gettext
import os.path

from ygo.utils import get_root_directory

class StringsDatabase:

	languages = dict()
	primary_language = ''

	def add(self, lang, short, path = None):
		lang = lang.lower()
		short = short.lower()
		l = {'short': short}
		if path is None:
			path = os.path.join(get_root_directory(), 'locale', short)
		l['path'] = path
		l['strings'] = self.__parse_strings(os.path.join(path, 'strings.conf'))
		self.languages[lang] = l
		self.primary_language = lang

	def __parse_strings(self, filename):
		if not os.path.isfile(filename):
			raise RuntimeError("strings.conf not found")
		res = {}
		with open(filename, 'r', encoding='utf-8') as fp:
			for line in fp:
				line = line.rstrip('\n')
				if not line.startswith('!') or line.startswith('!setcode'):
					continue
				type, id, s = line[1:].split(None, 2)
				if id.startswith('0x'):
					id = int(id, 16)
				else:
					id = int(id)
				if type not in res:
					res[type] = {}
				res[type][id] = s.replace('\xa0', ' ')
		return res

	def is_loaded(self, lang):
		return lang in self.languages

	def get_language(self, lang):
		return self.languages[lang]

	def _(self, lang, text):
		if lang == 'english':
			return gettext.NullTranslations().gettext(text)
		else:
			return gettext.translation('game', 'locale', languages=[self.get_language(lang)['short']], fallback=True).gettext(text)

	def get_short(self, lang):
		return self.get_language(lang)['short']

	def get_available_languages(self):
		return self.languages.keys()

	def get_long(self, short):
		short = short.lower()
		for l in self.languages.keys():
			if self.languages[l]['short'] == short:
				return l
		return self.primary_language

	def get_strings(self, lang):
		return self.get_language(lang)['strings']

	def get_string(self, text):
		return self.languages[self.primary_language]['strings'][text]

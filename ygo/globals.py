from .language_handler import LanguageHandler

language_handler: LanguageHandler = None
db = None

def strings(text):
    return language_handler.get_string(text)
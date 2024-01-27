setup: py_setup script locale/en/cards.cdb locale/zh/cards.cdb py_setup

py_setup:
	pip install -e .

script:
	ln -s third_party/ygopro-scripts script
	cd scripts; ln -s ../third_party/ygopro-scripts script

locale/en/cards.cdb:
	wget https://github.com/mycard/ygopro-database/raw/master/locales/en-US/cards.cdb -O $@

locale/zh/cards.cdb:
	wget https://github.com/mycard/ygopro-database/raw/master/locales/zh-CN/cards.cdb -O $@

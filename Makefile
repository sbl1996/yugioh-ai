setup: script locale/en/cards.cdb locale/zh/cards.cdb py_setup

py_setup: libygo.so
	pip install -e .

script: vendor/ygopro-scripts
	ln -s vendor/ygopro-scripts script

libygo.so: vendor/lua-5.3.5/src/liblua.a vendor/ygopro-core
	g++ -shared -fPIC -o $@ vendor/ygopro-core/*.cpp -Ivendor/lua-5.3.5/src -Lvendor/lua-5.3.5/src -llua -std=c++14

vendor/lua-5.3.5:
	cd vendor && wget --no-check-certificate https://www.lua.org/ftp/lua-5.3.5.tar.gz && tar xvf lua-5.3.5.tar.gz

vendor/lua-5.3.5/src/liblua.a: vendor/lua-5.3.5
	cd vendor/lua-5.3.5 && make linux CC=g++ CFLAGS='-O2 -fPIC'

vendor/ygopro-core:
	cd vendor && wget https://github.com/Fluorohydride/ygopro-core/archive/master.zip -O ygopro-core.zip
	unzip -q vendor/ygopro-core.zip -d vendor; mv vendor/ygopro-core-master $@
	cd $@ && sed -i '831c\int32 is_declarable(card_data const& cd, const std::vector<uint32>& opcode) {' playerop.cpp && sed -i '14i\#include <cstring>' field.h

vendor/ygopro-scripts:
	cd vendor && wget https://github.com/Fluorohydride/ygopro-scripts/archive/master.zip -O ygopro-scripts.zip
	unzip -q vendor/ygopro-scripts.zip -d vendor; mv vendor/ygopro-scripts-master $@

locale/en/cards.cdb:
	wget https://github.com/mycard/ygopro-database/raw/master/locales/en-US/cards.cdb -O $@

locale/zh/cards.cdb:
	wget https://github.com/mycard/ygopro-database/raw/master/locales/zh-CN/cards.cdb -O $@

clean:
	rm -rf vendor/ygopro-core vendor/ygopro-scripts vendor/lua-5.3.5 script
	rm -rf locale/en/cards.cdb locale/zh/cards.cdb
	rm -rf _duel.abi3.so libygo.so
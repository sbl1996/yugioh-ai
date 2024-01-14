setup: py_setup script locale/en/cards.cdb locale/zh/cards.cdb

py_setup:
	pip install -e .

script: vendor/ygopro-scripts
	ln -s vendor/ygopro-scripts script

libygo.so: vendor/lua-5.3.5/src/liblua.a vendor/ygopro-core
	g++ -shared -fPIC -o $@ vendor/ygopro-core/*.cpp -Ivendor/lua-5.3.5/src -Lvendor/lua-5.3.5/src -llua -std=c++14

vendor/lua-5.3.5:
	wget https://www.lua.org/ftp/lua-5.3.5.tar.gz
	cd vendor; tar xvf ../lua-5.3.5.tar.gz
	rm lua-5.3.5.tar.gz

vendor/lua-5.3.5/src/liblua.a: vendor/lua-5.3.5
	cd vendor/lua-5.3.5 && make linux CC=g++ CFLAGS='-O2 -fPIC'

vendor/ygopro-core:
	wget https://github.com/Fluorohydride/ygopro-core/archive/master.zip
	unzip -q master.zip -d vendor; mv vendor/ygopro-core-master $@
	rm master.zip
	cd $@ && patch -p0 < ../../etc/ygopro-core.patch && sed -i '14i\#include <cstring>' field.h

vendor/ygopro-scripts:
	wget https://github.com/Fluorohydride/ygopro-scripts/archive/master.zip
	unzip -q master.zip -d vendor; mv vendor/ygopro-scripts-master $@
	rm master.zip

locale/en/cards.cdb:
	wget https://github.com/mycard/ygopro-database/raw/master/locales/en-US/cards.cdb -O $@

locale/zh/cards.cdb:
	wget https://github.com/mycard/ygopro-database/raw/master/locales/zh-CN/cards.cdb -O $@
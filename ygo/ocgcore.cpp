#include "common.h"
#include "ocgapi.h"
#include "field.h"
#include <fstream>

#include <SQLiteCpp/SQLiteCpp.h>
#include <SQLiteCpp/VariadicBind.h>

#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>

namespace py = pybind11;

SQLite::Database *db;

uint32 card_reader_callback(uint32 code, struct card_data *card) {
    SQLite::Statement query(*db, "SELECT * FROM datas WHERE id=?");
    query.bind(1, code);
    query.executeStep();
    card->code = code;
    card->alias = query.getColumn("alias");
    card->setcode = query.getColumn("setcode").getInt64();
    card->type = query.getColumn("type");
    uint32 level_ = query.getColumn("level");
    card->level = level_ & 0xff;
    card->lscale = (level_ >> 24) & 0xff;
    card->rscale = (level_ >> 16) & 0xff;
    card->attack = query.getColumn("atk");
    card->defense = query.getColumn("def");
    if (card->type & TYPE_LINK) {
        card->link_marker = card->defense;
        card->defense = 0;
    }
    else {
        card->link_marker = 0;
    }
    card->race = query.getColumn("race");
    card->attribute = query.getColumn("attribute");
    return 0;
}

byte *script_reader_callback(const char *name, int *lenptr) {
    std::ifstream file(name, std::ios::binary);
    if (!file) {
        return nullptr;
    }
    file.seekg(0, std::ios::end);
    int len = file.tellg();
    file.seekg(0, std::ios::beg);
    byte *buf = new byte[len];
    file.read((char *)buf, len);
    *lenptr = len;
    return buf;
}

void init(const std::string &path) {
    db = new SQLite::Database(path, SQLite::OPEN_READONLY);
    set_card_reader(card_reader_callback);
    set_script_reader(script_reader_callback);
}


PYBIND11_MODULE(ocgcore, m) {
    m.def("init", &init);
    m.def("create_duel", &create_duel);
    m.def("start_duel", &start_duel);
    m.def("set_player_info", &set_player_info);
    m.def("new_card", &new_card);
    m.def("process", &process);
    m.def("get_message", [](intptr_t pduel, py::array_t<uint8> x) {
        return get_message(pduel, x.mutable_data());
    });
    m.def("end_duel", &end_duel);
    m.def("set_responsei", &set_responsei);
    m.def("set_responseb", [](intptr_t pduel, py::array_t<uint8> buf) {
        return set_responseb(pduel, buf.mutable_data());
    });
    m.def("query_field_card", [](intptr_t pduel, uint8 playerid, uint8 location, uint32 query_flag, py::array_t<uint8> buf, int32 use_cache) {
        return query_field_card(pduel, playerid, location, query_flag, buf.mutable_data(), use_cache);
    });
    m.def("query_card", [](intptr_t pduel, uint8 playerid, uint8 location, uint8 sequence, int32 query_flag, py::array_t<uint8> buf, int32 use_cache) {
        return query_card(pduel, playerid, location, sequence, query_flag, buf.mutable_data(), use_cache);
    });
    m.def("query_field_count", &query_field_count);
}
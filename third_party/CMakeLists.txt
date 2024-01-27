add_subdirectory(pybind11)
add_subdirectory(SQLiteCpp)

add_subdirectory(lua-cmake)

set(YCORE ${CMAKE_CURRENT_SOURCE_DIR}/ygopro-core)
set(YCORE_SRC ${CMAKE_CURRENT_SOURCE_DIR})
replace_line(
    ${YCORE}/playerop.cpp 831
    "int32 is_declarable(card_data const& cd, const std::vector<uint32>& opcode) {")

check_and_insert(${YCORE}/field.h 14 "#include <cstring>")

file(GLOB ycore_SRC CONFIGURE_DEPENDS
     "${YCORE}/*.h" "${YCORE}/*.cpp"
)
add_library(ycore SHARED ${ycore_SRC})
target_include_directories(ycore PUBLIC ${YCORE})
target_link_libraries(ycore PRIVATE lua_library)

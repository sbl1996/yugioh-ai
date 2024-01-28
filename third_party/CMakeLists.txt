add_subdirectory(pybind11)
add_subdirectory(SQLiteCpp)

set(BUILD_SHARED_LIBS ON)
add_subdirectory(lua-cmake)
set(BUILD_SHARED_LIBS OFF)

set(YCORE_DIR ${CMAKE_CURRENT_SOURCE_DIR}/ygopro-core)
set(YCORE_SRC ${CMAKE_CURRENT_SOURCE_DIR})
replace_line(
    ${YCORE_DIR}/playerop.cpp 831
    "int32 is_declarable(card_data const& cd, const std::vector<uint32>& opcode) {")

check_and_insert(${YCORE_DIR}/field.h 14 "#include <cstring>")

file(GLOB ycore_SRC CONFIGURE_DEPENDS
     "${YCORE_DIR}/*.h" "${YCORE_DIR}/*.cpp"
)
add_library(ycore SHARED ${ycore_SRC})
target_include_directories(ycore PUBLIC ${YCORE_DIR})
target_link_libraries(ycore PRIVATE lua_library)

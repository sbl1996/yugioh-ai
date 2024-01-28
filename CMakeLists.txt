cmake_minimum_required(VERSION 3.12)
project(ocgcore)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED True)

set(CMAKE_CXX_FLAGS_RELEASE "${CMAKE_CXX_FLAGS_RELEASE} -march=native")
set(CMAKE_C_FLAGS_RELEASE "${CMAKE_C_FLAGS_RELEASE} -march=native")

include("${PROJECT_SOURCE_DIR}/cmake/Helper.cmake")

add_subdirectory(third_party)

pybind11_add_module(ocgcore ygo/ocgcore.cpp)
target_link_libraries(ocgcore PRIVATE SQLiteCpp sqlite3 ycore)
pybind_move_target(ocgcore ygo)

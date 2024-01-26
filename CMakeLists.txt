cmake_minimum_required(VERSION 3.12)
project(ocgcore)
set(CMAKE_POLICY_DEFAULT_CMP0077 NEW)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED True)

set(CMAKE_CXX_FLAGS_RELEASE "${CMAKE_CXX_FLAGS_RELEASE} -march=native")
set(CMAKE_C_FLAGS_RELEASE "${CMAKE_C_FLAGS_RELEASE} -march=native")
set(BUILD_SHARED_LIBS ON)

include(${CMAKE_CURRENT_SOURCE_DIR}/PybindHelper.cmake)

add_subdirectory(third_party)

file(GLOB ygo_SRC CONFIGURE_DEPENDS
     "third_party/ygopro-core/*.h"
     "third_party/ygopro-core/*.cpp"
)


add_library(ygo2 SHARED ${ygo_SRC})
target_include_directories(ygo2 PRIVATE)
target_link_libraries(ygo2 PRIVATE lua_library)

pybind11_add_module(ocgcore ygo/ocgcore.cpp)
target_link_libraries(ocgcore PRIVATE SQLiteCpp sqlite3 ygo2 lua_library)
target_include_directories(
    ocgcore PRIVATE third_party/ygopro-core)
pybind_move_target(ocgcore ygo)

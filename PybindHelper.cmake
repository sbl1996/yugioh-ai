# set(CONDA_PREFIX $ENV{CONDA_PREFIX})
set(PYTHON_EXECUTABLE ${CONDA_PREFIX}/bin/python3)
set(PYTHON_LIBRARY ${CONDA_PREFIX}/lib/libpython3.so)

execute_process(
    COMMAND ${PYTHON_EXECUTABLE} -V
    OUTPUT_VARIABLE python_version_output
    ERROR_VARIABLE python_version_error
    RESULT_VARIABLE python_version_result
)

# move the build target to the python package
function(pybind_move_target target_name target_dir)
file(TO_CMAKE_PATH "${target_dir}" target_dir)
    set(install_dir ${CMAKE_CURRENT_SOURCE_DIR}/${target_dir} CACHE INTERNAL "")
    set(install_target_path ${install_dir}/$<TARGET_FILE_NAME:${target_name}> CACHE INTERNAL "")
    add_custom_command(
        TARGET ${target_name} POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
                $<TARGET_FILE:${target_name}> ${install_target_path}
        COMMAND ${CMAKE_COMMAND} -E echo "Move ${target_name} to ${install_dir}"
    )
endfunction()
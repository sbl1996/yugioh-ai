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

function(replace_line FILEPATH LINE_NUMBER NEW_LINE)
    # Use sed to replace the line at the specified line number
    execute_process(
        COMMAND sed -i "${LINE_NUMBER}c\\${NEW_LINE}" ${FILEPATH}
        RESULT_VARIABLE SED_RESULT
    )
    if(SED_RESULT)
        message(FATAL_ERROR "Failed to replace line in ${FILEPATH}.")
    endif()
endfunction()

function(check_and_insert FILEPATH LINE_NUMBER CONTENT)
    execute_process(
        COMMAND bash -c "sed -n ${LINE_NUMBER}p ${FILEPATH}"
        OUTPUT_VARIABLE line_content
        OUTPUT_STRIP_TRAILING_WHITESPACE
    )
    if(NOT "${line_content}" STREQUAL "${CONTENT}")
        execute_process(
            COMMAND bash -c "sed -i '${LINE_NUMBER}i\\${CONTENT}' ${FILEPATH}"
        )
        message("Insert line ${LINE_NUMBER} in ${FILEPATH} with '${CONTENT}'")
    endif()
endfunction()
cmake_minimum_required(VERSION 3.20)
project(compresso_zvga VERSION 0.1.0 LANGUAGES NONE)
set(CMAKE_INSTALL_BINDIR "bin" CACHE PATH "Executable directory")
find_package(Python3 3.8 REQUIRED COMPONENTS Interpreter)
option(COMPRESSO_VULKAN "Build the optional Vulkan compute backend" ON)
if(COMPRESSO_VULKAN)
  enable_language(CXX)
  find_package(Vulkan REQUIRED)
  find_program(GLSLANG_VALIDATOR glslangValidator REQUIRED)
  find_program(SPIRV_VAL spirv-val REQUIRED)
  add_custom_command(OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/rle_shader.h
    COMMAND ${GLSLANG_VALIDATOR} -V --target-env vulkan1.0 -o rle.spv ${CMAKE_CURRENT_SOURCE_DIR}/shaders/rle.comp
    COMMAND ${SPIRV_VAL} --target-env vulkan1.0 rle.spv
    COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/scripts/embed_shader.py rle.spv rle_shader.h
    DEPENDS shaders/rle.comp scripts/embed_shader.py VERBATIM)
  add_executable(compresso-vulkan native/vulkan_rle.cpp ${CMAKE_CURRENT_BINARY_DIR}/rle_shader.h)
  target_compile_features(compresso-vulkan PRIVATE cxx_std_17)
  target_compile_options(compresso-vulkan PRIVATE -Wall -Wextra -Wpedantic -Wno-missing-field-initializers)
  target_include_directories(compresso-vulkan PRIVATE ${CMAKE_CURRENT_BINARY_DIR})
  target_link_libraries(compresso-vulkan PRIVATE Vulkan::Vulkan)
  install(TARGETS compresso-vulkan RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})
endif()
# GNUInstallDirs needs a known architecture for its optional libdir default.
# A compiler-free CPU install uses the same portable lib/systemd/user layout.
set(CMAKE_INSTALL_LIBDIR "lib" CACHE PATH "Library directory")
include(GNUInstallDirs)
if(IS_ABSOLUTE "${CMAKE_INSTALL_BINDIR}" OR IS_ABSOLUTE "${CMAKE_INSTALL_LIBEXECDIR}")
  message(FATAL_ERROR "Use relative bindir and libexecdir for relocatable installation")
endif()
file(RELATIVE_PATH COMPRESSO_PACKAGE_FROM_BIN
  "${CMAKE_INSTALL_PREFIX}/${CMAKE_INSTALL_BINDIR}"
  "${CMAKE_INSTALL_PREFIX}/${CMAKE_INSTALL_LIBEXECDIR}/compresso")
install(DIRECTORY src/compresso_engine DESTINATION ${CMAKE_INSTALL_LIBEXECDIR}/compresso
  FILES_MATCHING PATTERN "*.py" PATTERN "__pycache__" EXCLUDE)
configure_file(scripts/compresso-engine.in compresso-engine @ONLY)
install(PROGRAMS ${CMAKE_CURRENT_BINARY_DIR}/compresso-engine DESTINATION ${CMAKE_INSTALL_BINDIR})
configure_file(systemd/compresso-engined.service.in compresso-engined.service @ONLY)
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/compresso-engined.service DESTINATION lib/systemd/user)

add_executable(tradebyte_gui terminal/gui.cpp)
target_link_libraries(tradebyte_gui PRIVATE ixwebsocket wsproto TradeByteLib)
target_include_directories(tradebyte_gui PRIVATE ${CMAKE_SOURCE_DIR}/terminal)

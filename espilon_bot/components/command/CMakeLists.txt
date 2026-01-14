idf_component_register(
    SRCS
        command.c
        command_async.c
    INCLUDE_DIRS .
    REQUIRES freertos core
)

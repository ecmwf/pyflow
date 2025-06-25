import inspect


def get_value_at_caller(target="self", stacklevel=2):
    """
    returns the value of a variable in the caller's frame. Useful for getting
    caller objects or variables at caller level, e.g, a Task name when defining its
    submit arguments on its Host.
    :param target: The name of the variable to retrieve from the caller's frame.
                   Defaults to "self", which is common in class methods.
    :param stacklevel: The number of frames to go back in the call stack.
                      Defaults to 2, which means it will look at the frame of immediate caller.
    """

    frame = inspect.stack()[1].frame
    for _ in range(stacklevel - 1):
        if frame is None:
            raise ValueError(f"No caller frame found with stacklevel {stacklevel}.")
        frame = frame.f_back
    # Get local variables in the caller's frame
    locals_ = frame.f_locals

    return locals_.get(target, None)

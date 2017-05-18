# coding=utf-8
"""
Customized error messages for Rero
"""


def error_message(e, command):
    """
    Detailed explanation of Discord error messages

    :param command:
    :param e:
    :return:
    """
    error = type(e).__name__
    if command == "prune":
        error_lookup = {
            "Forbidden": "I don't have proper permissions to delete messages",
            "HTTPException": "Deleting the messages failed",
            "ClientException": "Amount of messages to be deleted must be between 2 and 100"
        }
        try:
            return error_lookup[error]
        except KeyError:
            return None
    elif command == "purge":
        error_lookup = {
            "Forbidden": "I don't have proper permissions to delete messages",
            "HTTPException": "Purging the messages failed"
        }
        try:
            return error_lookup[error]
        except KeyError:
            return None
    elif command == "mute":
        error_lookup = {
            "Forbidden": "I don't have permissions to edit channel specific permissions",
            "HTTPException": "Editing channel specific permissions failed",
            "NotFound": "The channel specified was not found",
            "InvalidArgument": ":( we just encountered an error"
        }
        try:
            return error_lookup[error]
        except KeyError:
            return None
    elif command == "unmute":
        error_lookup = {
            "Forbidden": "I don't have permissions to delete channel specific permissions",
            "HTTPException": "Deleting channel specific permissions failed",
            "NotFound": "The channel specified was not found"
        }
        try:
            return error_lookup[error]
        except KeyError:
            return None
    else:
        return None

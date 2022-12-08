#!./env/bin/python3.11
import discord


def is_png(file: discord.Attachment):
    """
    checks if the file is png or not
    returns None if file is None
    """
    if file is None:
        return None
    elif file.content_type == 'image/png':
        return True
    else:
        return False


def calculate_credit(amount: int) -> int:
    if amount == 0:
        return 0
    amount -= 100
    return int(amount / 0.23)

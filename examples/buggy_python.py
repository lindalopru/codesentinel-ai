# ruff: noqa
# This file ships with intentional bugs for the `make demo` showcase.
# Disable linting so auto-fixers don't strip the planted issues.
"""CodeSentinel example fixture — Python source with 8 intentional issues.

Used by `make demo`. See docs/07_results.md for the expected findings.
"""

import os  # unused import (style)
import sys  # unused import (style)
import pickle


def charge_user(user_id, items=[]):  # mutable default argument (bug)
    total = 0
    for item in items:
        total += item.price
    query = "SELECT * FROM users WHERE id = " + str(user_id)  # SQL injection (security, critical)
    db.execute(query)  # noqa: F821
    return total


class UserService:  # missing docstring (documentation)
    def __init__(self, secret):
        print(f"Loaded service with secret={secret}")  # logs secret (security, high)
        self.cache = {}

    def authenticate(self, username, password):
        assert username and password, "creds required"  # assert for validation (bug, high) — stripped under -O
        if username == "admin":
            return True
        return False


def load_config(path):
    f = open(path)  # file not closed (bug)
    return f.read()


def run_code(snippet):
    return eval(snippet)  # eval on input (security, critical)


def load_user_data(blob):
    return pickle.loads(blob)  # unsafe deserialisation (security, high)


if __name__ == "__main__":
    print(charge_user(1))

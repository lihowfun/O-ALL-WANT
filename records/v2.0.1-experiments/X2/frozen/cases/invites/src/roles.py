from enum import Enum


class Role(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    GUEST = "guest"


RANK = {Role.OWNER: 3, Role.ADMIN: 2, Role.MEMBER: 1, Role.GUEST: 0}

# Guests are free collaborators and do not take a paid seat.
BILLABLE_ROLES = {Role.OWNER, Role.ADMIN, Role.MEMBER}


def can_assign(actor: Role, target: Role) -> bool:
    if actor == Role.OWNER:
        return True
    return RANK[actor] > RANK[target]


def is_billable(role: Role) -> bool:
    return role in BILLABLE_ROLES

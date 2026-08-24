"""
tests/test_permissions.py
Unit tests for hierarchy-safety logic using lightweight fake objects
(no real discord.py Member instances needed — those require a live gateway
connection to construct properly).
"""
from utils.permissions import is_hierarchy_safe, can_assign_role


class FakeRole:
    def __init__(self, position):
        self.position = position

    def __gt__(self, other):
        return self.position > other.position

    def __ge__(self, other):
        return self.position >= other.position


class FakeGuild:
    def __init__(self, owner_id):
        self.owner_id = owner_id


class FakeMember:
    def __init__(self, id_, top_role_position, guild):
        self.id = id_
        self.top_role = FakeRole(top_role_position)
        self.guild = guild


def test_owner_always_passes():
    guild = FakeGuild(owner_id=1)
    owner = FakeMember(1, top_role_position=0, guild=guild)
    target = FakeMember(2, top_role_position=100, guild=guild)
    assert is_hierarchy_safe(owner, target) is True


def test_lower_role_cannot_act_on_higher():
    guild = FakeGuild(owner_id=99)
    mod = FakeMember(1, top_role_position=5, guild=guild)
    admin_target = FakeMember(2, top_role_position=10, guild=guild)
    assert is_hierarchy_safe(mod, admin_target) is False


def test_higher_role_can_act_on_lower():
    guild = FakeGuild(owner_id=99)
    admin = FakeMember(1, top_role_position=10, guild=guild)
    member_target = FakeMember(2, top_role_position=1, guild=guild)
    assert is_hierarchy_safe(admin, member_target) is True


def test_cannot_act_on_self():
    guild = FakeGuild(owner_id=99)
    mod = FakeMember(1, top_role_position=5, guild=guild)
    assert is_hierarchy_safe(mod, mod) is False


def test_cannot_assign_role_above_own():
    guild = FakeGuild(owner_id=99)
    mod = FakeMember(1, top_role_position=5, guild=guild)
    high_role = FakeRole(position=10)
    assert can_assign_role(mod, high_role) is False


def test_can_assign_role_below_own():
    guild = FakeGuild(owner_id=99)
    admin = FakeMember(1, top_role_position=10, guild=guild)
    low_role = FakeRole(position=2)
    assert can_assign_role(admin, low_role) is True

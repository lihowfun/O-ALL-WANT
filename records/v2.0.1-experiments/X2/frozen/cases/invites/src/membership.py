from dataclasses import dataclass

from roles import Role, is_billable


@dataclass
class Membership:
    workspace_id: str
    user_id: str
    role: Role


class MembershipStore:
    def __init__(self, billing):
        self.billing = billing

    def add_member(self, tx, workspace_id: str, user_id: str, role: Role) -> Membership:
        tx.execute(
            "INSERT INTO memberships (workspace_id, user_id, role) VALUES (%s, %s, %s) "
            "ON CONFLICT (workspace_id, user_id) DO UPDATE SET role = EXCLUDED.role",
            (workspace_id, user_id, role.value),
        )
        if is_billable(role):
            tx.execute(
                "UPDATE workspaces SET seats_used = seats_used + 1 WHERE id = %s",
                (workspace_id,),
            )
            self.billing.report_seat_change(workspace_id, +1)
        return Membership(workspace_id, user_id, role)

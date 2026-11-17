from typing import Dict, Set

class Role:
    OWNER = "Owner"
    ADMIN = "Admin"
    DEVELOPER = "Developer"
    VIEWER = "Viewer"

class Action:
    MANAGE_REPOSITORY = "MANAGE_REPOSITORY"      # Delete repo, disconnect, regenerate webhook secret
    MANAGE_SETTINGS = "MANAGE_SETTINGS"          # Notification channels, monitored branches
    MANAGE_MEMBERS = "MANAGE_MEMBERS"            # Promote/demote members, change app roles
    TRIGGER_ANALYSIS = "TRIGGER_ANALYSIS"        # Run manual analysis or simulated test event
    APPLY_REMEDIATION = "APPLY_REMEDIATION"      # Trigger automated fix / staging retry
    VIEW_REPORTS = "VIEW_REPORTS"                # View dashboards, AI reports, logs

# Role hierarchy capability map
ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    Role.OWNER: {
        Action.MANAGE_REPOSITORY,
        Action.MANAGE_SETTINGS,
        Action.MANAGE_MEMBERS,
        Action.TRIGGER_ANALYSIS,
        Action.APPLY_REMEDIATION,
        Action.VIEW_REPORTS
    },
    Role.ADMIN: {
        Action.MANAGE_SETTINGS,
        Action.MANAGE_MEMBERS,
        Action.TRIGGER_ANALYSIS,
        Action.APPLY_REMEDIATION,
        Action.VIEW_REPORTS
    },
    Role.DEVELOPER: {
        Action.TRIGGER_ANALYSIS,
        Action.APPLY_REMEDIATION,
        Action.VIEW_REPORTS
    },
    Role.VIEWER: {
        Action.VIEW_REPORTS
    }
}

class RBACException(Exception):
    def __init__(self, message: str, status_code: int = 403):
        super().__init__(message)
        self.status_code = status_code

def map_github_to_app_role(github_permission: str, is_creator: bool = False) -> str:
    """
    Translates GitHub repository permissions into Application RBAC roles:
    - admin + creator -> Owner
    - admin -> Admin (or Owner)
    - maintain -> Admin
    - write / push -> Developer
    - read / pull -> Viewer
    """
    perm = github_permission.lower().strip()
    if perm == "admin":
        return Role.OWNER if is_creator else Role.ADMIN
    elif perm == "maintain":
        return Role.ADMIN
    elif perm in ["write", "push"]:
        return Role.DEVELOPER
    elif perm in ["read", "pull"]:
        return Role.VIEWER
    else:
        raise RBACException("Access denied: You do not have sufficient permissions to access this repository.")

def has_permission(user_role: str, action: str) -> bool:
    """Checks whether the given role is allowed to perform the target action."""
    allowed_actions = ROLE_PERMISSIONS.get(user_role, set())
    return action in allowed_actions

def enforce_permission(user_role: str, action: str) -> None:
    """Raises 403 Forbidden exception if the user does not possess the requisite capability."""
    if not has_permission(user_role, action):
        raise RBACException(
            f"Forbidden: Role '{user_role}' does not have permission to perform '{action}'."
        )


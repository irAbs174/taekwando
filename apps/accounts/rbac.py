"""Role-to-Group and granular Django Permission matrix synchronization."""
from __future__ import annotations

from django.contrib.auth.models import Group, Permission

from apps.accounts.models import STAFF_ROLES, UserRole

# Maps each role group to explicit (app_label, codename) permissions.
ROLE_PERMISSION_MAP: dict[str, list[tuple[str, str]]] = {
    UserRole.CONTENT_ADMIN: [
        # Blog
        ("blog", "view_category"),
        ("blog", "add_category"),
        ("blog", "change_category"),
        ("blog", "delete_category"),
        ("blog", "view_categorytranslation"),
        ("blog", "add_categorytranslation"),
        ("blog", "change_categorytranslation"),
        ("blog", "delete_categorytranslation"),
        ("blog", "view_tag"),
        ("blog", "add_tag"),
        ("blog", "change_tag"),
        ("blog", "delete_tag"),
        ("blog", "view_post"),
        ("blog", "add_post"),
        ("blog", "change_post"),
        ("blog", "delete_post"),
        ("blog", "view_posttranslation"),
        ("blog", "add_posttranslation"),
        ("blog", "change_posttranslation"),
        ("blog", "delete_posttranslation"),
        # Products
        ("products", "view_productcategory"),
        ("products", "add_productcategory"),
        ("products", "change_productcategory"),
        ("products", "delete_productcategory"),
        ("products", "view_productcategorytranslation"),
        ("products", "add_productcategorytranslation"),
        ("products", "change_productcategorytranslation"),
        ("products", "delete_productcategorytranslation"),
        ("products", "view_product"),
        ("products", "add_product"),
        ("products", "change_product"),
        ("products", "delete_product"),
        ("products", "view_producttranslation"),
        ("products", "add_producttranslation"),
        ("products", "change_producttranslation"),
        ("products", "delete_producttranslation"),
        ("products", "view_productimage"),
        ("products", "add_productimage"),
        ("products", "change_productimage"),
        ("products", "delete_productimage"),
        # Pages
        ("pages", "view_page"),
        ("pages", "add_page"),
        ("pages", "change_page"),
        ("pages", "delete_page"),
        ("pages", "view_pagetranslation"),
        ("pages", "add_pagetranslation"),
        ("pages", "change_pagetranslation"),
        ("pages", "delete_pagetranslation"),
        # SEO
        ("seo", "view_seometadata"),
        ("seo", "add_seometadata"),
        ("seo", "change_seometadata"),
        ("seo", "delete_seometadata"),
        ("seo", "view_seotranslation"),
        ("seo", "add_seotranslation"),
        ("seo", "change_seotranslation"),
        ("seo", "delete_seotranslation"),
        # Contact messages (read/review)
        ("contact", "view_contactmessage"),
        ("contact", "change_contactmessage"),
    ],
    UserRole.CLUB_MANAGER: [
        # Users & Member profiles
        ("accounts", "view_user"),
        ("accounts", "add_user"),
        ("accounts", "change_user"),
        ("members", "view_memberprofile"),
        ("members", "add_memberprofile"),
        ("members", "change_memberprofile"),
        ("members", "approve_membership"),
        # Belts
        ("belts", "view_belttype"),
        ("belts", "add_belttype"),
        ("belts", "change_belttype"),
        ("belts", "delete_belttype"),
        ("belts", "view_belthistory"),
        ("belts", "add_belthistory"),
        ("belts", "change_belthistory"),
        ("belts", "moderate_belthistory"),
        # Medals
        ("medals", "view_medal"),
        ("medals", "add_medal"),
        ("medals", "change_medal"),
        ("medals", "moderate_medal"),
        # Achievements
        ("achievements", "view_achievement"),
        ("achievements", "add_achievement"),
        ("achievements", "change_achievement"),
        ("achievements", "moderate_achievement"),
        # Competitions
        ("competitions", "view_competition"),
        ("competitions", "add_competition"),
        ("competitions", "change_competition"),
        ("competitions", "delete_competition"),
        ("competitions", "view_competitionparticipation"),
        ("competitions", "add_competitionparticipation"),
        ("competitions", "change_competitionparticipation"),
        ("competitions", "moderate_competitionparticipation"),
        # Social Activities
        ("activities", "view_socialactivity"),
        ("activities", "change_socialactivity"),
        ("activities", "moderate_socialactivity"),
        # Contact, ReviewLogs & AuditLogs
        ("contact", "view_contactmessage"),
        ("contact", "change_contactmessage"),
        ("core", "view_reviewlog"),
        ("audit_logs", "view_auditlog"),
    ],
    UserRole.MODERATOR: [
        ("members", "view_memberprofile"),
        ("activities", "view_socialactivity"),
        ("activities", "change_socialactivity"),
        ("activities", "moderate_socialactivity"),
        ("achievements", "view_achievement"),
        ("achievements", "change_achievement"),
        ("achievements", "moderate_achievement"),
        ("medals", "view_medal"),
        ("medals", "change_medal"),
        ("medals", "moderate_medal"),
        ("belts", "view_belthistory"),
        ("belts", "change_belthistory"),
        ("belts", "moderate_belthistory"),
        ("competitions", "view_competition"),
        ("competitions", "view_competitionparticipation"),
        ("competitions", "change_competitionparticipation"),
        ("competitions", "moderate_competitionparticipation"),
        ("contact", "view_contactmessage"),
        ("contact", "change_contactmessage"),
        ("core", "view_reviewlog"),
    ],
    UserRole.MEMBER: [
        # Own-object access is enforced at the queryset/object level
    ],
}


def ensure_role_groups() -> dict[str, Group]:
    """Idempotently create all 5 RBAC groups and assign their granular permissions."""
    groups: dict[str, Group] = {}
    all_perms = {
        (p.content_type.app_label, p.codename): p
        for p in Permission.objects.select_related("content_type").all()
    }

    for role_code, _label in UserRole.choices:
        group, _ = Group.objects.get_or_create(name=role_code)
        groups[role_code] = group
        if role_code == UserRole.SUPER_ADMIN:
            group.permissions.set(list(all_perms.values()))
        else:
            desired = [
                all_perms[key]
                for key in ROLE_PERMISSION_MAP.get(role_code, [])
                if key in all_perms
            ]
            group.permissions.set(desired)
    return groups


def sync_user_role_group(user) -> None:
    """
    Synchronize a user's Django Group membership and staff flags with `user.role`.
    Removes stale role groups while preserving any custom non-role groups.
    """
    if not user.pk:
        return
    role_names = {code for code, _ in UserRole.choices}
    target_group, created = Group.objects.get_or_create(name=user.role)
    if created or (user.role != UserRole.MEMBER and not target_group.permissions.exists()):
        ensure_role_groups()
        target_group = Group.objects.get(name=user.role)

    stale_groups = user.groups.filter(name__in=(role_names - {user.role}))
    if stale_groups.exists():
        user.groups.remove(*stale_groups)
    if not user.groups.filter(pk=target_group.pk).exists():
        user.groups.add(target_group)

    desired_staff = user.role in STAFF_ROLES
    desired_super = user.role == UserRole.SUPER_ADMIN
    if user.is_staff != desired_staff or user.is_superuser != desired_super:
        user.is_staff = desired_staff
        user.is_superuser = desired_super
        user.__class__.objects.filter(pk=user.pk).update(
            is_staff=desired_staff,
            is_superuser=desired_super,
        )

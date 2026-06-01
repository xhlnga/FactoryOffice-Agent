from sqlalchemy import inspect, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.integrations.core.base import BaseIntegrationProvider, OrgProvider
from app.integrations.core.registry import IntegrationProviderRegistry, provider_registry
from app.integrations.core.schemas import (
    DepartmentRecord,
    IntegrationCapability,
    IntegrationEventStatus,
    IntegrationPlatform,
    OrgSyncResult,
    ProviderContext,
    UserRecord,
)
from app.integrations.providers import register_builtin_providers
from app.models.base import DepartmentStatus, UserRole, UserStatus, utc_now
from app.models.department import Department
from app.models.external_id_mapping import ExternalIdMapping
from app.models.user import User


class OrgSyncService:
    """组织架构同步服务。

    从 Provider 读取组织快照；传入数据库会同步落库到 departments/users，
    并写 external_id_mappings，方便后续外部平台状态回写。
    """

    def __init__(self, registry: IntegrationProviderRegistry | None = None) -> None:
        if registry is None:
            register_builtin_providers(replace=True)
        self.registry = registry or provider_registry

    def preview(
        self,
        *,
        platform: IntegrationPlatform,
        config: dict | None = None,
        enterprise_id: int | None = None,
    ) -> dict:
        """预览组织架构同步结果，不写数据库。"""
        provider = self._org_provider(platform, config=config, enterprise_id=enterprise_id)
        departments = provider.list_departments()
        users = provider.list_users()
        return {
            "platform": platform.value,
            "enterprise_id": enterprise_id,
            "department_count": len(departments),
            "user_count": len(users),
            "disabled_user_count": sum(1 for user in users if not user.active),
            "departments": [department.model_dump(mode="json") for department in departments],
            "users": [user.model_dump(mode="json") for user in users],
        }

    def sync(
        self,
        *,
        platform: IntegrationPlatform,
        config: dict | None = None,
        enterprise_id: int | None = None,
        db: Session | None = None,
        commit: bool = True,
    ) -> OrgSyncResult:
        """执行组织架构同步。

        没传 db 时只返回规范化快照；传入 db 时会执行 upsert。
        """
        provider = self._org_provider(platform, config=config, enterprise_id=enterprise_id)
        departments: list[DepartmentRecord] = provider.list_departments()
        users: list[UserRecord] = provider.list_users()
        metadata = {
            "platform": platform.value,
            "departments": [department.model_dump(mode="json") for department in departments],
            "users": [user.model_dump(mode="json") for user in users],
        }
        persisted = {}
        if db is not None and enterprise_id is not None:
            persisted = self._upsert_org_snapshot(
                db,
                platform=platform,
                enterprise_id=enterprise_id,
                departments=departments,
                users=users,
                commit=commit,
            )
            metadata.update(persisted)
        return OrgSyncResult(
            department_count=len(departments),
            user_count=len(users),
            disabled_user_count=sum(1 for user in users if not user.active),
            message="组织架构同步完成。" if persisted else "组织架构同步快照已生成。",
            metadata=metadata,
        )

    def _org_provider(
        self,
        platform: IntegrationPlatform,
        *,
        config: dict | None,
        enterprise_id: int | None,
    ) -> OrgProvider:
        provider: BaseIntegrationProvider = self.registry.get(
            platform,
            ProviderContext(platform=platform, enterprise_id=enterprise_id, config=config or {}),
        )
        provider.ensure_capability(IntegrationCapability.ORG)
        return provider  # type: ignore[return-value]

    def _upsert_org_snapshot(
        self,
        db: Session,
        *,
        platform: IntegrationPlatform,
        enterprise_id: int,
        departments: list[DepartmentRecord],
        users: list[UserRecord],
        commit: bool,
    ) -> dict:
        """把外部组织快照写入本地组织表。

        真实企业里组织同步必须可重复执行，所以这里全部按外部 ID 做 upsert。
        """
        required_tables = {"departments", "users", "external_id_mappings"}
        if not all(_table_exists(db, table_name) for table_name in required_tables):
            return {"persisted": False, "reason": "org_tables_not_ready"}

        department_map = self._upsert_departments(db, platform, enterprise_id, departments)
        user_count = self._upsert_users(db, platform, enterprise_id, users, department_map)
        if commit:
            db.commit()
        else:
            db.flush()
        return {
            "persisted": True,
            "persisted_department_count": len(department_map),
            "persisted_user_count": user_count,
        }

    def _upsert_departments(
        self,
        db: Session,
        platform: IntegrationPlatform,
        enterprise_id: int,
        departments: list[DepartmentRecord],
    ) -> dict[str, Department]:
        external_ids = [item.external_department_id for item in departments]
        existing_departments = {
            item.external_department_id: item
            for item in db.scalars(
                select(Department)
                .where(Department.enterprise_id == enterprise_id)
                .where(Department.external_department_id.in_(external_ids))
            )
            if item.external_department_id
        }

        department_map: dict[str, Department] = {}
        for record in departments:
            department = existing_departments.get(record.external_department_id)
            if department is None:
                department = Department(
                    enterprise_id=enterprise_id,
                    external_department_id=record.external_department_id,
                    name=record.name,
                )
                db.add(department)
            department.name = record.name
            department.sort_order = record.order or 0
            department.status = DepartmentStatus.ACTIVE if record.active else DepartmentStatus.DISABLED
            department_map[record.external_department_id] = department

        db.flush()

        for record in departments:
            department = department_map[record.external_department_id]
            parent = (
                department_map.get(record.parent_external_department_id)
                if record.parent_external_department_id
                else None
            )
            department.parent_id = parent.id if parent else None
            department.path = f"{parent.path or parent.name}/{department.name}" if parent else department.name
            self._upsert_external_mapping(
                db,
                platform=platform,
                enterprise_id=enterprise_id,
                object_type="department",
                local_id=department.id,
                external_id=record.external_department_id,
            )

        db.flush()
        return department_map

    def _upsert_users(
        self,
        db: Session,
        platform: IntegrationPlatform,
        enterprise_id: int,
        users: list[UserRecord],
        department_map: dict[str, Department],
    ) -> int:
        count = 0
        for record in users:
            user = db.scalar(
                select(User)
                .where(User.enterprise_id == enterprise_id)
                .where(User.external_user_id == record.external_user_id)
                .limit(1)
            )
            if user is None:
                user = User(
                    username=_unique_username(db, _username_from_external_id(platform, record.external_user_id)),
                    role=UserRole.EMPLOYEE,
                    enterprise_id=enterprise_id,
                    external_user_id=record.external_user_id,
                )
                db.add(user)

            first_department = department_map.get(record.external_department_ids[0]) if record.external_department_ids else None
            user.external_user_id = record.external_user_id
            user.username = user.username or _unique_username(db, _username_from_external_id(platform, record.external_user_id))
            user.department_id = first_department.id if first_department else None
            user.department = first_department.name if first_department else None
            user.position = record.position
            user.mobile_hash = record.mobile_hash
            user.email = record.email
            user.status = UserStatus.ACTIVE if record.active else UserStatus.DISABLED
            db.flush()

            self._upsert_external_mapping(
                db,
                platform=platform,
                enterprise_id=enterprise_id,
                object_type="user",
                local_id=user.id,
                external_id=record.external_user_id,
            )
            count += 1
        return count

    def _upsert_external_mapping(
        self,
        db: Session,
        *,
        platform: IntegrationPlatform,
        enterprise_id: int,
        object_type: str,
        local_id: int,
        external_id: str,
    ) -> None:
        mapping = db.scalar(
            select(ExternalIdMapping)
            .where(ExternalIdMapping.enterprise_id == enterprise_id)
            .where(ExternalIdMapping.object_type == object_type)
            .where(ExternalIdMapping.external_system == platform.value)
            .where(ExternalIdMapping.external_id == external_id)
            .limit(1)
        )
        if mapping is None:
            mapping = ExternalIdMapping(
                enterprise_id=enterprise_id,
                object_type=object_type,
                external_system=platform.value,
                external_id=external_id,
            )
            db.add(mapping)
        mapping.local_id = str(local_id)
        mapping.sync_status = IntegrationEventStatus.SUCCESS.value
        mapping.last_error = None
        mapping.retry_count = 0
        mapping.last_sync_at = utc_now()


def _username_from_external_id(platform: IntegrationPlatform, external_user_id: str) -> str:
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in external_user_id.lower()).strip("_")
    return f"{platform.value}_{cleaned or 'user'}"


def _unique_username(db: Session, base_username: str) -> str:
    username = base_username[:64]
    if db.scalar(select(User.id).where(User.username == username).limit(1)) is None:
        return username
    for index in range(2, 1000):
        suffix = f"_{index}"
        candidate = f"{base_username[: 64 - len(suffix)]}{suffix}"
        if db.scalar(select(User.id).where(User.username == candidate).limit(1)) is None:
            return candidate
    raise RuntimeError("无法生成唯一用户名。")


def _table_exists(db: Session, table_name: str) -> bool:
    try:
        return bool(inspect(db.connection()).has_table(table_name))
    except SQLAlchemyError:
        db.rollback()
        return False
    except Exception:
        return False

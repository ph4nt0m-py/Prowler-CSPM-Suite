import json
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.credential import CredentialAuthMethod, CredentialProvider


class AwsStaticKeysIn(BaseModel):
    access_key_id: str = Field(..., min_length=16, max_length=128)
    secret_access_key: str = Field(..., min_length=1, max_length=128)
    session_token: str | None = None


class AwsAssumeRoleIn(BaseModel):
    role_arn: str = Field(..., min_length=1, max_length=512)
    external_id: str | None = Field(None, max_length=256)
    base: AwsStaticKeysIn


class AzureServicePrincipalIn(BaseModel):
    tenant_id: str = Field(..., min_length=1, max_length=128)
    client_id: str = Field(..., min_length=1, max_length=128)
    client_secret: str = Field(..., min_length=1, max_length=512)


class GcpServiceAccountIn(BaseModel):
    """Paste full GCP service account JSON (object with type, project_id, private_key, etc.)."""

    service_account_json: str = Field(..., min_length=10, max_length=65536)

    def payload_dict(self) -> dict:
        try:
            data = json.loads(self.service_account_json)
        except json.JSONDecodeError as e:
            raise ValueError("service_account_json must be valid JSON") from e
        if not isinstance(data, dict):
            raise ValueError("service_account_json must be a JSON object")
        return {"service_account": data}


class CredentialCreate(BaseModel):
    label: str = Field(default="default", max_length=255)
    provider: CredentialProvider = CredentialProvider.aws
    auth_method: CredentialAuthMethod
    aws_static: AwsStaticKeysIn | None = None
    aws_assume_role: AwsAssumeRoleIn | None = None
    azure_sp: AzureServicePrincipalIn | None = None
    gcp_sa: GcpServiceAccountIn | None = None

    def payload_dict(self) -> dict:
        if self.provider == CredentialProvider.aws:
            if self.auth_method == CredentialAuthMethod.static_keys:
                if not self.aws_static:
                    raise ValueError("aws_static required for AWS static keys")
                return self.aws_static.model_dump()
            if self.auth_method == CredentialAuthMethod.assume_role:
                if not self.aws_assume_role:
                    raise ValueError("aws_assume_role required")
                return self.aws_assume_role.model_dump()
            raise ValueError("Unsupported AWS auth_method")
        if self.provider == CredentialProvider.azure:
            if self.auth_method != CredentialAuthMethod.static_keys:
                raise ValueError("Azure credentials use static_keys (service principal) in this API")
            if not self.azure_sp:
                raise ValueError("azure_sp required for Azure")
            return {"azure": self.azure_sp.model_dump()}
        if self.provider == CredentialProvider.gcp:
            if self.auth_method != CredentialAuthMethod.static_keys:
                raise ValueError("GCP credentials use static_keys (service account JSON) in this API")
            if not self.gcp_sa:
                raise ValueError("gcp_sa required for GCP")
            return self.gcp_sa.payload_dict()
        raise ValueError("Unsupported provider")


class CredentialOut(BaseModel):
    id: UUID
    client_id: UUID
    provider: CredentialProvider
    label: str
    auth_method: CredentialAuthMethod
    created_at: datetime

    model_config = {"from_attributes": True}


class CredentialTestResult(BaseModel):
    account: str
    arn: str

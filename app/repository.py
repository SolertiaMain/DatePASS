from __future__ import annotations

from typing import Any

import boto3
from boto3.dynamodb.conditions import Attr

from .config import get_settings
from .models import InvitationStatus, utc_now_iso


class InvitationRepository:
    def __init__(self) -> None:
        settings = get_settings()
        self._table = boto3.resource("dynamodb", region_name=settings.aws_region).Table(settings.table_name)

    def create(self, item: dict[str, Any]) -> dict[str, Any]:
        self._table.put_item(Item=item, ConditionExpression="attribute_not_exists(id)")
        return item

    def get(self, invitation_id: str) -> dict[str, Any] | None:
        response = self._table.get_item(Key={"id": invitation_id}, ConsistentRead=True)
        return response.get("Item")

    def set_pass_key(self, invitation_id: str, pass_s3_key: str) -> None:
        self._table.update_item(
            Key={"id": invitation_id},
            UpdateExpression="SET pass_s3_key = :key, updated_at = :now",
            ExpressionAttributeValues={":key": pass_s3_key, ":now": utc_now_iso()},
        )

    def respond(self, invitation_id: str, status: InvitationStatus) -> dict[str, Any] | None:
        now = utc_now_iso()
        timestamp_field = "accepted_at" if status == InvitationStatus.accepted else "declined_at"
        try:
            response = self._table.update_item(
                Key={"id": invitation_id},
                ConditionExpression=Attr("id").exists(),
                UpdateExpression=f"SET #status = :status, updated_at = :now, {timestamp_field} = :now",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={":status": status.value, ":now": now},
                ReturnValues="ALL_NEW",
            )
            return response.get("Attributes")
        except self._table.meta.client.exceptions.ConditionalCheckFailedException:
            return None

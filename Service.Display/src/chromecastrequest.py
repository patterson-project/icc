from typing import Optional
from pydantic import BaseModel, Field
from objectid import PydanticObjectId
from fastapi.encoders import jsonable_encoder


class ChromecastRequest(BaseModel):
    id: Optional[PydanticObjectId] = Field(None, alias="_id")
    target: PydanticObjectId
    path: str

    def to_json(self):
        return jsonable_encoder(self, exclude_none=True)

    def to_bson(self):
        data = self.dict(by_alias=True, exclude_none=True)
        if data.get("_id") is None:
            data.pop("_id", None)
        return data

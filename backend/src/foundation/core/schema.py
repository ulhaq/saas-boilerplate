from pydantic import BaseModel, ConfigDict


class ResponseSchema(BaseModel):
    """Base for response models.

    A field with a default is always serialised, so the OpenAPI schema should
    mark it required - otherwise the frontend's generated API types make it
    optional and every caller has to handle a value the API always sends.
    """

    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

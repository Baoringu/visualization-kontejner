from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)


class OrganizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    locale: str
    timezone: str


class MeOut(BaseModel):
    id: UUID
    email: EmailStr
    display_name: str
    role: str
    organization: OrganizationOut
    csrf_token: str


class MessageOut(BaseModel):
    message: str


class HealthOut(BaseModel):
    status: str
    service: str
    database: str


class ProductCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)


class ProductOut(ProductCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    revision: int
    is_active: bool


class PackagingUnitCreate(BaseModel):
    product_id: UUID
    code: str = Field(min_length=1, max_length=100)
    units_per_package: int = Field(gt=0)
    length_mm: int = Field(gt=0)
    width_mm: int = Field(gt=0)
    height_mm: int = Field(gt=0)
    mass_g: int = Field(gt=0)


class PackagingUnitOut(PackagingUnitCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    revision: int
    is_verified: bool
    evidence_ref: str | None
    top_load_limit_g: int | None
    allow_upright_90: bool


class PackagingVerification(BaseModel):
    expected_revision: int = Field(gt=0)
    evidence_ref: str = Field(min_length=3, max_length=500)
    top_load_limit_g: int | None = Field(default=None, ge=0)
    allow_upright_90: bool = False


class CustomerCreate(BaseModel):
    external_ref: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    contact_name: str | None = Field(default=None, max_length=200)
    contact_email: EmailStr | None = None
    contact_phone: str | None = Field(default=None, max_length=50)
    ship_to_name: str | None = Field(default=None, max_length=200)
    ship_to_address_line1: str | None = Field(default=None, max_length=200)
    ship_to_address_line2: str | None = Field(default=None, max_length=200)
    ship_to_city: str | None = Field(default=None, max_length=120)
    ship_to_postal_code: str | None = Field(default=None, max_length=30)
    ship_to_country_code: str | None = Field(default=None, min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")
    delivery_instructions: str | None = Field(default=None, max_length=1000)


class CustomerUpdate(CustomerCreate):
    expected_revision: int = Field(gt=0)


class CustomerOut(CustomerCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    revision: int


class OrderCreate(BaseModel):
    order_ref: str = Field(min_length=1, max_length=100)
    customer_id: UUID


class OrderOut(OrderCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    status: str
    revision: int


class OrderLineCreate(BaseModel):
    packaging_unit_id: UUID
    line_no: int = Field(gt=0)
    quantity_units: int = Field(gt=0)


class OrderLineOut(OrderLineCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    allocated_units: int


class OrderDetailOut(OrderOut):
    lines: list[OrderLineOut]


class CartLineWrite(BaseModel):
    packaging_unit_id: UUID
    quantity_cartons: int = Field(gt=0, le=5000)


class CartReplace(BaseModel):
    expected_revision: int = Field(gt=0)
    lines: list[CartLineWrite] = Field(max_length=200)


class ShipmentCreate(BaseModel):
    shipment_ref: str = Field(min_length=1, max_length=100)
    lines: list[OrderLineCreate] = Field(min_length=1)


class ShipmentOut(BaseModel):
    id: UUID
    order_id: UUID
    shipment_ref: str
    status: str
    revision: int
    lines: list[OrderLineOut]


class PalletTypeCreate(BaseModel):
    code: str = Field(min_length=1, max_length=100)
    length_mm: int = Field(gt=0)
    width_mm: int = Field(gt=0)
    deck_height_mm: int = Field(gt=0)
    max_total_height_mm: int = Field(gt=0)
    max_cargo_mass_g: int = Field(gt=0)
    tare_mass_g: int = Field(ge=0)
    available_count: int = Field(gt=0, le=100)
    support_model: str = Field(pattern="^solid_deck$")
    evidence_ref: str = Field(min_length=3, max_length=500)


class PalletTypeOut(PalletTypeCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    revision: int


class PreflightRequest(BaseModel):
    pallet_type_id: UUID


class PreflightOut(BaseModel):
    ready: bool
    blockers: list[str]
    requested_units: int
    requested_cartons: int | None


class RunCreate(BaseModel):
    pallet_type_id: UUID
    expected_shipment_revision: int = Field(gt=0)
    strategy: Literal["quick", "best_fit"] = "quick"
    evaluation_budget: int = Field(default=250_000, ge=1, le=2_000_000)


class RunOut(BaseModel):
    id: UUID
    shipment_id: UUID
    status: str
    termination_reason: str | None
    error_code: str | None
    plan_id: UUID | None


class PlacementOut(BaseModel):
    instance_id: str
    pallet_index: int
    x_mm: int
    y_mm: int
    z_mm: int
    orientation_code: str
    length_mm: int
    width_mm: int
    height_mm: int
    sku: str | None = None
    mass_g: int | None = None


class UnplacedOut(BaseModel):
    instance_id: str
    reason: str
    sku: str | None = None


class InstructionOut(BaseModel):
    sequence_no: int
    instance_id: str
    pallet_index: int


class LayoutPalletOut(BaseModel):
    length_mm: int
    width_mm: int
    deck_height_mm: int
    max_total_height_mm: int
    max_cargo_mass_g: int
    tare_mass_g: int
    available_count: int
    support_model: str


class LayoutCartonOut(BaseModel):
    sku: str
    length_mm: int
    width_mm: int
    height_mm: int
    mass_g: int
    top_load_limit_g: int | None
    allowed_orientations: list[str]
    name: str | None = None
    source_order_line_id: UUID | None = None
    instance_ids: list[str] = Field(default_factory=list)


class SearchOut(BaseModel):
    termination_reason: str
    evaluations_completed: int
    candidates_completed: int = 1
    strategy: Literal["quick", "best_fit"] = "quick"


class ModelChecksOut(BaseModel):
    geometry: str
    column_vertical_load: str
    instruction_prefix: str = "not_evaluated"
    transport_dynamics: str


class LayoutOut(BaseModel):
    scope: str
    placed: list[PlacementOut]
    unplaced: list[UnplacedOut]
    instructions: list[InstructionOut]
    requested_instances: int
    placed_instances: int
    unplaced_instances: int
    pallet_count: int
    pallet: LayoutPalletOut
    carton: LayoutCartonOut | None = None
    cartons: list[LayoutCartonOut] = Field(default_factory=list)
    cargo_mass_g: int
    loaded_mass_g: int
    cargo_height_mm: int
    loaded_height_mm: int
    model_checks: ModelChecksOut
    search: SearchOut


class PlanOut(BaseModel):
    id: UUID
    run_id: UUID
    shipment_id: UUID
    input_hash: str
    layout_hash: str
    validation_status: str
    validator_version: str
    instruction_version: str
    layout: LayoutOut

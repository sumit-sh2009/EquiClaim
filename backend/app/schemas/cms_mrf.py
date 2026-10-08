"""CMS Hospital Price Transparency wire-format models (45 CFR § 180.50).

These models mirror the **CMS Data Dictionary v3.0** column/attribute names
verbatim (pipe-delimited CSV "Tall" headers via `populate_by_name` aliases).
They are the *ingestion boundary* only — the MRF ingestion pipeline (Phase 3)
parses raw CMS files into these models, then maps them into the internal
`MRFBenchmark` domain model (integer cents, EquiClaim-native shape). Keeping
the two decoupled means a future CMS schema revision only touches this file.

Reference: https://github.com/CMSgov/hospital-price-transparency/blob/master/documentation/CSV/README.md
Regulation: https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-E/part-180/subpart-B/section-180.50
"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.money import dollars_to_cents

CodeType = Literal[
    "CPT",
    "NDC",
    "HCPCS",
    "RC",
    "ICD",
    "DRG",
    "MS-DRG",
    "R-DRG",
    "S-DRG",
    "APS-DRG",
    "AP-DRG",
    "APR-DRG",
    "APC",
    "LOCAL",
    "EAPG",
    "HIPPS",
    "CDT",
    "CDM",
    "TRIS-DRG",
    "CMG",
    "MS-LTC-DRG",
]


class CmsMrfCodePair(BaseModel):
    """JSON `code_information[]` item — attributes `code`, `type`."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    code: str = Field(description="Billing/account code (CSV header code|[i])")
    type: CodeType = Field(description="Code type (CSV header code|[i]|type)")


class CmsMrfTallChargeSlice(BaseModel):
    """One row of the CMS CSV **Tall** standard-charge template.

    Field names use the literal pipe-delimited CMS column headers as
    aliases (e.g. `standard_charge|gross`) so a raw CSV `DictReader` row can
    be validated directly with `CmsMrfTallChargeSlice.model_validate(row)`.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    code_1: str | None = Field(default=None, alias="code|1")
    code_1_type: CodeType | None = Field(default=None, alias="code|1|type")
    description: str | None = Field(default=None, alias="description")

    standard_charge_gross: Decimal | None = Field(default=None, alias="standard_charge|gross")
    standard_charge_discounted_cash: Decimal | None = Field(
        default=None, alias="standard_charge|discounted_cash"
    )
    payer_name: str | None = None
    plan_name: str | None = None
    standard_charge_negotiated_dollar: Decimal | None = Field(
        default=None, alias="standard_charge|negotiated_dollar"
    )
    standard_charge_negotiated_percentage: float | None = Field(
        default=None, alias="standard_charge|negotiated_percentage"
    )
    standard_charge_negotiated_algorithm: str | None = Field(
        default=None, alias="standard_charge|negotiated_algorithm"
    )

    @model_validator(mode="before")
    @classmethod
    def blank_csv_cells_are_none(cls, data: object) -> object:
        """CSV `DictReader` yields `""` for empty cells; CMS treats blanks as absent.

        Without this, every optional numeric field (e.g. `standard_charge|
        negotiated_percentage`, routinely blank on Tall-format rows where a
        dollar amount was used instead) would fail float coercion on `""`.
        """
        if isinstance(data, dict):
            return {k: (None if v == "" else v) for k, v in data.items()}
        return data

    @model_validator(mode="after")
    def code_and_type_paired(self) -> CmsMrfTallChargeSlice:
        """CMS CSV dictionary conditional requirement #3: code and type travel together."""
        if (self.code_1 is None) ^ (self.code_1_type is None):
            raise ValueError("code|1 and code|1|type must be encoded together")
        return self

    def to_cents(self, value: Decimal | None) -> int | None:
        """Convert a CMS dollar amount to integer cents (half-up)."""
        return dollars_to_cents(value)

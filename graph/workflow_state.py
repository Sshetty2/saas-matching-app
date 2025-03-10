from typing import Optional, TypedDict
from pydantic import BaseModel, Field

# TODO: consolidate models


class MatchResultPydantic(BaseModel):
    id: int = Field(
        ...,
        description="The ID of the CPE record that best matches the software alias.",
    )
    reasoning: str = Field(
        ...,
        description="A brief explanation of why this match was chosen and the confidence score given.",
    )


# need seperate models for validation
class AnalysisResultPydantic(BaseModel):
    best_match: MatchResultPydantic = Field(
        ...,
        description="The best match for the software alias.",
    )
    possible_matches: list[MatchResultPydantic] = Field(
        ...,
        description="A list of possible matches for the software alias.",
    )


class SoftwareInfoPydantic(BaseModel):
    product: str = Field(
        ..., description="The parsed product name from the software alias."
    )
    vendor: str = Field(
        ...,
        description="The parsed vendor name from the software alias. If inferred, this should be noted in 'inference_reasoning'.",
    )
    version: str = Field(
        ...,
        description="The version number of the software if available; otherwise 'N/A'.",
    )
    inference_reasoning: str = Field(
        ...,
        description="If the vendor was inferred, provide a short explanation. Otherwise, return 'N/A'.",
    )


class MatchResult(TypedDict):
    id: int
    reasoning: str


# need seperate models for langchain validation
class AnalysisResult(TypedDict):
    best_match: MatchResult
    possible_matches: list[MatchResult]


class SoftwareInfo(TypedDict):
    product: str
    vendor: str
    version: str
    inference_reasoning: str


class AuditResultPydantic(BaseModel):
    restart: bool
    reasoning: str


class AuditResult(TypedDict):
    restart: bool
    reasoning: str


class WorkflowState(TypedDict):
    software_alias: str
    software_info: Optional[SoftwareInfo]
    cpe_matches: Optional[AnalysisResult]
    product_search_results: Optional[list[str]]
    matched_products: Optional[list[str]]
    cpe_results: Optional[list]
    error: Optional[str]
    info: Optional[str]
    exact_match: Optional[dict]
    attempts: Optional[int]
    audit_result: Optional[AuditResult]
    parse_results: Optional[list[SoftwareInfo]]
    attempts: Optional[int]


class CPEResult(TypedDict):
    CPEConfigurationID: str
    ConfigurationsName: str
    NVD_Header: str
    NVD_Version: str
    Part: str
    Vendor: str
    Product: str
    Version: str
    Updates: str
    Edition: str
    SW_Edition: str
    Target_SW: str
    Target_HW: str
    Language: str
    Other: str
    OrgID: str
    StatusID: str
    CreatedOn: str
    CreatedBy: str

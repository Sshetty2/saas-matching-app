from typing import Optional, TypedDict, Any
from pydantic import BaseModel, Field
import pyodbc

## TODO: consolidate models


# need seperate models for validation
class AnalysisResultPydantic(BaseModel):
    match_type: str = Field(
        ...,
        description="The type of match: 'Exact Match', 'Close Match', 'General Match', or 'No Match'.",
    )
    confidence_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Confidence score (0-100) based on how closely the software alias matches the CPE record.",
    )
    matched_cpe: str = Field(
        ..., description="The CPE string that best matches the software alias."
    )
    reasoning: str = Field(
        ...,
        description="A brief explanation of why this match was chosen and the confidence score given.",
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


# need seperate models for langchain validation
class AnalysisResult(TypedDict):
    match_type: str
    confidence_score: int
    matched_cpe: str
    reasoning: str


class SoftwareInfo(TypedDict):
    product: str
    vendor: str
    version: str
    inference_reasoning: str


class WorkflowState(TypedDict):
    software_alias: str
    software_info: Optional[SoftwareInfo]
    cpe_match: Optional[list[AnalysisResult]]
    cpe_results: Optional[list]
    top_matches: Optional[list]
    error: Optional[str]
    info: Optional[str]
    query_type: Optional[
        str
    ]  ## used to track the type of query used to find the CPE results
    query_results: Optional[
        int
    ]  ## used to track the number of results found from the query
    query_attempts: Optional[
        int
    ]  ## used to track the number of attempts to query the database
    parse_results: Optional[list[SoftwareInfo]]
    product_vector_store: Optional[Any]
    vendor_vector_store: Optional[Any]
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

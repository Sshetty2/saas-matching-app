from typing import Optional, TypedDict
from pydantic import BaseModel
import pyodbc


## TODO: consolidate models


# need seperate model langchain validation
class AnalysisResult(TypedDict):
    match_type: str
    confidence_score: int
    matched_cpe: str
    reasoning: str


# need seperate model langchain validation
class AnalysisResultPydantic(BaseModel):
    match_type: str
    confidence_score: int
    matched_cpe: str
    reasoning: str


# need seperate model langchain validation
class SoftwareInfo(TypedDict):
    product: str
    vendor: str
    version: str
    inference_reasoning: str


## need seperate model for validation
class SoftwareInfoPydantic(BaseModel):
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

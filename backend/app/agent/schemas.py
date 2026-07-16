from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class LogInteractionExtraction(BaseModel):
    hcp_name: Optional[str] = Field(description="The name of the HCP, e.g. 'Dr. Smith'")
    interaction_type: Optional[str] = Field(description="Type of interaction, e.g. 'meeting', 'call'")
    date: Optional[str] = Field(description="Date of interaction, e.g. 'today', '2023-10-01'")
    time: Optional[str] = Field(description="Time of interaction")
    attendees: Optional[List[str]] = Field(description="List of attendees")
    topics_discussed: Optional[str] = Field(description="Topics discussed")
    sentiment: Optional[Literal["positive", "neutral", "negative"]] = Field(description="Sentiment of the interaction")
    materials_shared: Optional[List[str]] = Field(description="List of materials shared")
    samples_distributed: Optional[List[str]] = Field(description="List of samples distributed")
class EditInteractionExtraction(BaseModel):
    hcp_name: Optional[str] = Field(None, description="The name of the HCP, ONLY if requested to change")
    interaction_type: Optional[str] = Field(None, description="Type of interaction, ONLY if requested to change")
    date: Optional[str] = Field(None, description="Date of interaction, ONLY if requested to change")
    time: Optional[str] = Field(None, description="Time of interaction, ONLY if requested to change")
    attendees: Optional[List[str]] = Field(None, description="List of attendees, ONLY if requested to change")
    topics_discussed: Optional[str] = Field(None, description="Topics discussed, ONLY if requested to change")
    sentiment: Optional[Literal["positive", "neutral", "negative"]] = Field(None, description="Sentiment, ONLY if requested to change")
    materials_shared: Optional[List[str]] = Field(None, description="Materials shared, ONLY if requested to change")
    samples_distributed: Optional[List[str]] = Field(None, description="Samples distributed, ONLY if requested to change")

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, Enum
from sqlalchemy.dialects.postgresql import JSONB, ENUM
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum

class SentimentEnum(str, enum.Enum):
    positive = "positive"
    neutral = "neutral"
    negative = "negative"

class ComplianceFlagEnum(str, enum.Enum):
    clear = "clear"
    review = "review"

class HCP(Base):
    __tablename__ = "hcps"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    specialty = Column(String, nullable=False)
    region = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    interactions = relationship("HCPInteraction", back_populates="hcp")

class HCPInteraction(Base):
    __tablename__ = "hcp_interactions"

    id = Column(Integer, primary_key=True, index=True)
    hcp_id = Column(Integer, ForeignKey("hcps.id"), nullable=False)
    rep_id = Column(Integer)
    interaction_type = Column(String)
    date = Column(String)
    time = Column(String)
    attendees = Column(JSONB)
    topics_discussed = Column(Text)
    materials_shared = Column(JSONB)
    samples_distributed = Column(JSONB)
    sentiment = Column(Enum(SentimentEnum, name="sentiment_enum", create_type=False))
    outcomes = Column(Text)
    follow_up_actions = Column(Text)
    suggested_follow_ups = Column(JSONB)
    compliance_flag = Column(Enum(ComplianceFlagEnum, name="compliance_flag_enum", create_type=False), nullable=True)
    voice_consent_at = Column(DateTime(timezone=True), nullable=True)
    voice_transcript = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    hcp = relationship("HCP", back_populates="interactions")
    messages = relationship("ChatMessage", back_populates="interaction")
    tool_calls = relationship("AgentToolCall", back_populates="interaction")

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    interaction_id = Column(Integer, ForeignKey("hcp_interactions.id"), nullable=False)
    role = Column(String, nullable=False) # user or assistant
    content = Column(Text, nullable=False)
    tool_calls = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    interaction = relationship("HCPInteraction", back_populates="messages")

class AgentToolCall(Base):
    __tablename__ = "agent_tool_calls"

    id = Column(Integer, primary_key=True, index=True)
    interaction_id = Column(Integer, ForeignKey("hcp_interactions.id"), nullable=False)
    tool_name = Column(String, nullable=False)
    input = Column(JSONB)
    output = Column(JSONB)
    before_state = Column(JSONB)
    after_state = Column(JSONB)
    confidence = Column(Float, nullable=True)
    model_used = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    interaction = relationship("HCPInteraction", back_populates="tool_calls")

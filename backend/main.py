from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Literal
from datetime import datetime, timedelta
import random
import uuid

app = FastAPI(title="ACD Monitor API", version="1.0.0")

# CORS middleware for Vercel frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your Vercel domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models matching our Zod schemas
class Source(BaseModel):
    name: str
    freshnessSec: int
    quality: float


class RiskSummary(BaseModel):
    score: int
    band: Literal["LOW", "AMBER", "RED"]
    confidence: int
    updatedAt: str
    timeframe: Literal["30d", "6m", "1y", "ytd"]
    source: Source


class Metric(BaseModel):
    key: Literal["stability", "synchronization", "environmentalSensitivity"]
    label: str
    score: int
    direction: Literal["UP", "DOWN", "FLAT"]
    note: Optional[str] = None


class MetricsOverview(BaseModel):
    timeframe: Literal["30d", "6m", "1y", "ytd"]
    updatedAt: str
    items: List[Metric]


class HealthPoint(BaseModel):
    ts: str
    convergence: int
    dataIntegrity: int
    evidenceChain: int
    runtimeStability: int


class HealthRun(BaseModel):
    updatedAt: str
    summary: dict
    spark: List[HealthPoint]
    source: Source


class Event(BaseModel):
    id: str
    ts: str
    type: Literal["MARKET", "COORDINATION", "INFO_FLOW", "REGIME_SWITCH", "USER"]
    title: str
    description: str
    severity: Literal["LOW", "MEDIUM", "HIGH"]
    riskScore: int
    durationMin: Optional[int] = None
    affects: Optional[List[str]] = None


class EventsResponse(BaseModel):
    timeframe: Literal["30d", "6m", "1y", "ytd"]
    updatedAt: str
    items: List[Event]


class DataSource(BaseModel):
    id: str
    name: str
    tier: Literal["T1", "T2", "T3", "T4"]
    status: Literal["OK", "DEGRADED", "DOWN"]
    freshnessSec: int
    quality: float


class DataSources(BaseModel):
    updatedAt: str
    items: List[DataSource]


class EvidenceExport(BaseModel):
    requestedAt: str
    status: Literal["READY", "QUEUED"]
    url: Optional[str] = None
    bundleId: str
    estSeconds: Optional[int] = None


# Mock data generators
def generate_risk_summary(timeframe: str = "ytd") -> RiskSummary:
    return RiskSummary(
        score=16,
        band="LOW",
        confidence=97,
        updatedAt=datetime.now().isoformat(),
        timeframe=timeframe,
        source=Source(name="Algorithmic Cartel Detection Engine", freshnessSec=20, quality=0.96),
    )


def generate_metrics_overview(timeframe: str = "ytd") -> MetricsOverview:
    return MetricsOverview(
        timeframe=timeframe,
        updatedAt=datetime.now().isoformat(),
        items=[
            Metric(
                key="stability",
                label="Market Stability",
                score=85,
                direction="UP",
                note="Improved coordination patterns",
            ),
            Metric(
                key="synchronization",
                label="Price Synchronization",
                score=23,
                direction="FLAT",
                note="Within normal competitive range",
            ),
            Metric(
                key="environmentalSensitivity",
                label="Environmental Sensitivity",
                score=67,
                direction="DOWN",
                note="Reduced sensitivity to external factors",
            ),
        ],
    )


def generate_health_run() -> HealthRun:
    now = datetime.now()
    spark_data = []

    # Generate 12 data points for the last 2 hours
    for i in range(12):
        ts = now - timedelta(minutes=10 * i)
        spark_data.append(
            HealthPoint(
                ts=ts.isoformat(),
                convergence=random.randint(85, 95),
                dataIntegrity=random.randint(90, 98),
                evidenceChain=random.randint(88, 96),
                runtimeStability=random.randint(92, 99),
            )
        )

    return HealthRun(
        updatedAt=now.isoformat(),
        summary={"systemHealth": 94, "complianceReadiness": 89, "band": "PASS"},
        spark=spark_data,
        source=Source(name="Health Monitoring System", freshnessSec=15, quality=0.98),
    )


def generate_events(timeframe: str = "ytd") -> EventsResponse:
    now = datetime.now()
    events = [
        Event(
            id=str(uuid.uuid4()),
            ts=(now - timedelta(minutes=30)).isoformat(),
            type="MARKET",
            title="Market coordination",
            description="Detected potential coordination patterns in price movements",
            severity="LOW",
            riskScore=16,
            affects=["FNB", "Absa", "Standard Bank"],
        ),
        Event(
            id=str(uuid.uuid4()),
            ts=(now - timedelta(minutes=25)).isoformat(),
            type="INFO_FLOW",
            title="Information flow anomaly",
            description="Unusual information propagation detected between algorithms",
            severity="LOW",
            riskScore=12,
        ),
        Event(
            id=str(uuid.uuid4()),
            ts=(now - timedelta(minutes=20)).isoformat(),
            type="REGIME_SWITCH",
            title="Regime switch",
            description="Market regime transition from competitive to coordinated state",
            severity="LOW",
            riskScore=18,
        ),
        Event(
            id=str(uuid.uuid4()),
            ts=(now - timedelta(minutes=15)).isoformat(),
            type="COORDINATION",
            title="Price leadership change",
            description="Shift in price leadership patterns detected",
            severity="MEDIUM",
            riskScore=35,
            durationMin=45,
        ),
        Event(
            id=str(uuid.uuid4()),
            ts=(now - timedelta(minutes=10)).isoformat(),
            type="MARKET",
            title="Volume spike",
            description="Unusual volume increase in coordinated trading",
            severity="LOW",
            riskScore=8,
        ),
    ]

    return EventsResponse(timeframe=timeframe, updatedAt=now.isoformat(), items=events)


def generate_data_sources() -> DataSources:
    return DataSources(
        updatedAt=datetime.now().isoformat(),
        items=[
            DataSource(
                id="bloomberg",
                name="Bloomberg Terminal",
                tier="T1",
                status="OK",
                freshnessSec=15,
                quality=0.98,
            ),
            DataSource(
                id="reuters",
                name="Reuters Market Data",
                tier="T1",
                status="OK",
                freshnessSec=12,
                quality=0.96,
            ),
            DataSource(
                id="internal",
                name="Internal Trading Feed",
                tier="T2",
                status="OK",
                freshnessSec=8,
                quality=0.94,
            ),
            DataSource(
                id="alternative",
                name="Alternative Data Provider",
                tier="T3",
                status="DEGRADED",
                freshnessSec=45,
                quality=0.87,
            ),
        ],
    )


def generate_evidence_export() -> EvidenceExport:
    now = datetime.now()
    bundle_id = f"acd-evidence-{now.strftime('%Y%m%d%H%M')}"

    return EvidenceExport(
        requestedAt=now.isoformat(),
        status="READY",
        url=f"https://api.example.com/evidence/{bundle_id}.zip",
        bundleId=bundle_id,
    )


# API Endpoints
@app.get("/")
async def root():
    return {"message": "ACD Monitor API", "version": "1.0.0"}


@app.get("/api/risk/summary", response_model=RiskSummary)
async def get_risk_summary(timeframe: str = Query("ytd", regex="^(30d|6m|1y|ytd)$")):
    return generate_risk_summary(timeframe)


@app.get("/api/metrics/overview", response_model=MetricsOverview)
async def get_metrics_overview(timeframe: str = Query("ytd", regex="^(30d|6m|1y|ytd)$")):
    return generate_metrics_overview(timeframe)


@app.get("/api/health/run", response_model=HealthRun)
async def get_health_run():
    return generate_health_run()


@app.get("/api/events", response_model=EventsResponse)
async def get_events(timeframe: str = Query("ytd", regex="^(30d|6m|1y|ytd)$")):
    return generate_events(timeframe)


@app.get("/api/datasources/status", response_model=DataSources)
async def get_data_sources():
    return generate_data_sources()


@app.get("/api/evidence/export", response_model=EvidenceExport)
async def get_evidence_export():
    return generate_evidence_export()


@app.get("/api/_status")
async def get_status():
    return {"status": "healthy", "timestamp": datetime.now().isoformat(), "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

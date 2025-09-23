from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Literal
from datetime import datetime, timedelta
import random
import uuid
import io
import zipfile
import logging

logger = logging.getLogger(__name__)

app = FastAPI(title="ACD Monitor API", version="1.0.0")

# CORS middleware for Vercel frontend
PROD_ORIGIN = "https://acd-monitor.vercel.app"
PREVIEW_ORIGIN = (
    "https://acd-monitor-git-feat-pr-51da97-ygorfrancisco-gmailcoms-projects.vercel.app"
)
PREVIEW_REGEX = r"^https://.*\.vercel\.app$"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Temporarily allow all origins for debugging
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
    allow_credentials=False,
    max_age=86400,
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


@app.get("/api/evidence/export/zip")
async def get_evidence_export_zip():
    """Generate and download evidence package as ZIP file"""
    try:
        # Create ZIP file in memory
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            # Add summary.md
            summary_content = f"""# Algorithmic Cartel Detection - Evidence Package

## Executive Summary

This evidence package contains comprehensive analysis results from the Algorithmic Cartel Detection (ACD) system, implementing the methodological framework outlined in Brief 55+.

## Methodology Overview

### Brief 55+ Framework
- **Information Cascade Vulnerability Model (ICVM)**: Analyzes how information flows between market participants
- **Vulnerability Mapping Model (VMM)**: Identifies structural vulnerabilities in algorithmic trading systems
- **Regime Detection**: Monitors for shifts between competitive and coordinated market states

### Detection Methods
1. **Price Leadership Analysis**: Identifies dominant price-setting behaviors
2. **Volume Synchronization**: Detects coordinated trading patterns
3. **Information Flow Mapping**: Tracks data dependencies between algorithms
4. **Regime Switching Models**: Statistical models to detect coordination phases

## Current Risk Assessment

- **Overall Risk Score**: 16/100 (LOW)
- **Confidence Level**: 97%
- **Risk Band**: LOW
- **Assessment Period**: Year-to-Date (YTD)
- **Last Updated**: {datetime.now().isoformat()}

## Key Findings

1. **Market Coordination**: Minimal evidence of algorithmic coordination
2. **Information Flow**: Normal competitive information patterns observed
3. **Regime Stability**: Market operating in competitive regime
4. **Compliance Status**: All metrics within acceptable thresholds

## Data Sources

- Bloomberg Terminal: 98% quality, 15s freshness
- Reuters Market Data: 96% quality, 12s freshness  
- Internal Trading Feed: 94% quality, 8s freshness
- Alternative Data Provider: 87% quality, 45s freshness (DEGRADED)

## Recommendations

1. Continue monitoring for regime changes
2. Maintain current surveillance protocols
3. Review quarterly for emerging patterns
4. Escalate if risk score exceeds 40

---
Generated by ACD Monitor API v1.0.0
{datetime.now().isoformat()}"""

            zip_file.writestr("summary.md", summary_content)

            # Add risk_summary.json
            risk_data = generate_risk_summary()
            zip_file.writestr("risk_summary.json", risk_data.model_dump_json(indent=2))

            # Add events.csv
            events_data = generate_events()
            csv_content = "timestamp,event_type,severity,risk_band\n"
            for event in events_data.items:
                csv_content += f"{event.ts},{event.type},{event.severity},{'LOW' if event.riskScore < 30 else 'AMBER' if event.riskScore < 70 else 'HIGH'}\n"
            zip_file.writestr("events.csv", csv_content)

            # Add data_source.json
            sources_data = generate_data_sources()
            zip_file.writestr("data_source.json", sources_data.model_dump_json(indent=2))

        zip_buffer.seek(0)
        zip_bytes = zip_buffer.getvalue()

        # Generate filename
        now = datetime.now()
        filename = f"acd-evidence-{now.strftime('%Y%m%d%H%M')}.zip"

        # Return ZIP file with proper headers
        return Response(
            content=zip_bytes,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "no-store",
            },
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate evidence package: {str(e)}"
        )


@app.get("/api/_status")
async def get_status():
    return {"status": "healthy", "timestamp": datetime.now().isoformat(), "version": "1.0.0"}


@app.get("/_status")
async def heartbeat():
    return {"ok": True, "ts": datetime.utcnow().isoformat() + "Z", "freshnessSec": 3}


# Binance Exchange Endpoints
@app.get("/exchanges/binance/overview")
async def get_binance_overview(
    symbol: str = Query("BTCUSDT", description="Trading symbol"),
    tf: str = Query("5m", description="Timeframe"),
):
    """Get Binance overview data (ticker + OHLCV)"""
    try:
        from src.exchanges.service import get_exchange_service

        service = get_exchange_service()
        data = await service.fetch_overview(symbol, tf)
        return data

    except ValueError as ve:
        error_msg = str(ve)
        if error_msg == "binance_no_ohlcv":
            logger.error(f"Binance no OHLCV data: {ve}")
            raise HTTPException(
                status_code=502,
                detail={"error": "binance_no_ohlcv", "message": "No recent candles available"},
            )
        elif error_msg == "binance_invalid_symbol":
            logger.error(f"Binance invalid symbol: {ve}")
            raise HTTPException(
                status_code=502,
                detail={"error": "binance_invalid_symbol", "message": "Invalid trading symbol"},
            )
        else:
            logger.error(f"Binance error: {ve}")
            raise HTTPException(
                status_code=502, detail={"error": "binance_unavailable", "message": str(ve)}
            )
    except Exception as e:
        logger.error(f"Binance overview failed: {e}")
        raise HTTPException(
            status_code=502, detail={"error": "binance_unavailable", "message": str(e)}
        )


@app.get("/exchanges/binance/depth")
async def get_binance_depth(
    symbol: str = Query("BTCUSDT", description="Trading symbol"),
    limit: int = Query(10, description="Number of price levels"),
):
    """Get Binance order book depth"""
    try:
        from src.exchanges.service import get_exchange_service

        service = get_exchange_service()
        data = await service.fetch_depth(symbol, limit)
        return data

    except Exception as e:
        logger.error(f"Binance depth failed: {e}")
        raise HTTPException(
            status_code=502, detail={"error": "binance_unavailable", "message": str(e)}
        )


@app.get("/exchanges/binance/ping")
async def ping_binance():
    """Health check for Binance API"""
    try:
        from src.exchanges.service import get_exchange_service

        service = get_exchange_service()
        is_healthy = await service.ping_binance()
        return {"healthy": is_healthy, "venue": "binance"}

    except Exception as e:
        logger.error(f"Binance ping failed: {e}")
        return {"healthy": False, "venue": "binance", "error": str(e)}


@app.get("/exchanges/binance/raw-klines")
async def get_binance_raw_klines(
    symbol: str = Query("BTCUSDT", description="Trading symbol"),
    interval: str = Query("5m", description="Timeframe interval"),
    limit: int = Query(50, description="Number of klines to fetch"),
):
    """Debug route to get raw klines data from Binance"""
    try:
        from src.exchanges.binance import get_binance_api

        api = await get_binance_api()
        data = await api.get_ohlcv(symbol, interval)

        # Return debug info
        return {
            "count": len(data),
            "sample": {"first": data[0] if data else None, "last": data[-1] if data else None},
            "symbol": symbol,
            "interval": interval,
            "requested_limit": limit,
        }

    except ValueError as ve:
        error_msg = str(ve)
        if error_msg == "binance_no_ohlcv":
            return {
                "count": 0,
                "sample": {"first": None, "last": None},
                "symbol": symbol,
                "interval": interval,
                "requested_limit": limit,
                "error": "binance_no_ohlcv",
            }
        else:
            return {
                "count": 0,
                "sample": {"first": None, "last": None},
                "symbol": symbol,
                "interval": interval,
                "requested_limit": limit,
                "error": error_msg,
            }
    except Exception as e:
        logger.error(f"Raw klines debug failed: {e}")
        return {
            "count": 0,
            "sample": {"first": None, "last": None},
            "symbol": symbol,
            "interval": interval,
            "requested_limit": limit,
            "error": str(e),
        }


# Multi-Exchange Endpoints
@app.get("/exchanges/kraken/overview")
async def get_kraken_overview(
    symbol: str = Query("BTCUSDT", description="Trading symbol"),
    tf: str = Query("5m", description="Timeframe"),
):
    """Get Kraken overview data (ticker + OHLCV)"""
    try:
        from src.exchanges.service import get_exchange_service

        service = get_exchange_service()
        data = await service.fetch_overview_multi("kraken", symbol, tf)
        return data

    except Exception as e:
        logger.error(f"Kraken overview failed: {e}")
        raise HTTPException(
            status_code=502, detail={"error": "kraken_unavailable", "message": str(e)}
        )


@app.get("/exchanges/okx/overview")
async def get_okx_overview(
    symbol: str = Query("BTCUSDT", description="Trading symbol"),
    tf: str = Query("5m", description="Timeframe"),
):
    """Get OKX overview data (ticker + OHLCV)"""
    try:
        from src.exchanges.service import get_exchange_service

        service = get_exchange_service()
        data = await service.fetch_overview_multi("okx", symbol, tf)
        return data

    except Exception as e:
        logger.error(f"OKX overview failed: {e}")
        raise HTTPException(status_code=502, detail={"error": "okx_unavailable", "message": str(e)})


@app.get("/exchanges/bybit/overview")
async def get_bybit_overview(
    symbol: str = Query("BTCUSDT", description="Trading symbol"),
    tf: str = Query("5m", description="Timeframe"),
):
    """Get Bybit overview data (ticker + OHLCV)"""
    try:
        from src.exchanges.service import get_exchange_service

        service = get_exchange_service()
        data = await service.fetch_overview_multi("bybit", symbol, tf)
        return data

    except Exception as e:
        logger.error(f"Bybit overview failed: {e}")
        raise HTTPException(
            status_code=502, detail={"error": "bybit_unavailable", "message": str(e)}
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

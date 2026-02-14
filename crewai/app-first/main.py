"""
CrewAI Research Service
=======================
FastAPI wrapper that exposes a multi-agent research crew.
- Researcher agent: breaks down the topic into key questions
- Writer agent: synthesizes research into a polished article

Called from AnythingLLM via custom agent skill or direct API.
"""

import os
import logging
import asyncio
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from crewai import Agent, Task, Crew, Process, LLM

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
QDRANT_HOST = os.getenv("QDRANT_HOST", "http://qdrant:6333")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="CrewAI Research Service",
    description="Multi-agent research crew powered by Ollama",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------
class ResearchRequest(BaseModel):
    topic: str = Field(..., description="The topic to research")
    depth: Optional[str] = Field(
        "medium",
        description="Research depth: brief, medium, or deep",
    )


class ResearchResponse(BaseModel):
    topic: str
    result: str
    duration_seconds: float
    model: str
    agents_used: list[str]


# ---------------------------------------------------------------------------
# LLM setup
# ---------------------------------------------------------------------------
def get_llm() -> LLM:
    """Create an Ollama-backed LLM instance for CrewAI."""
    return LLM(
        model=f"ollama/{OLLAMA_MODEL}",
        base_url=OLLAMA_HOST,
    )


# ---------------------------------------------------------------------------
# Agent definitions
# ---------------------------------------------------------------------------
def build_crew(topic: str, depth: str = "medium") -> Crew:
    llm = get_llm()

    depth_instructions = {
        "brief": "Keep your research concise - 3-5 key points maximum.",
        "medium": "Provide a thorough analysis covering major aspects of the topic.",
        "deep": "Do an exhaustive deep-dive. Cover history, current state, "
                "key players, controversies, and future outlook.",
    }

    # --- Researcher Agent ---
    researcher = Agent(
        role="Senior Research Analyst",
        goal=f"Conduct thorough research on: {topic}",
        backstory=(
            "You are a seasoned research analyst with decades of experience. "
            "You excel at breaking down complex topics into key findings, "
            "identifying important patterns, and separating fact from opinion. "
            "You always cite your reasoning and note areas of uncertainty."
        ),
        llm=llm,
        verbose=True,
        max_iter=5,
    )

    # --- Writer Agent ---
    writer = Agent(
        role="Expert Content Writer",
        goal="Transform research findings into a clear, engaging article",
        backstory=(
            "You are an award-winning writer known for making complex topics "
            "accessible. You structure information logically, use clear language, "
            "and always ensure accuracy. You write in a professional but "
            "engaging tone."
        ),
        llm=llm,
        verbose=True,
        max_iter=5,
    )

    # --- Tasks ---
    research_task = Task(
        description=(
            f"Research the following topic thoroughly: {topic}\n\n"
            f"Instructions: {depth_instructions.get(depth, depth_instructions['medium'])}\n\n"
            "Provide:\n"
            "1. Key findings and facts\n"
            "2. Different perspectives or viewpoints\n"
            "3. Important context\n"
            "4. Areas where information is uncertain or debated"
        ),
        expected_output=(
            "A structured research brief with clearly labeled sections: "
            "Key Findings, Context, Perspectives, and Open Questions."
        ),
        agent=researcher,
    )

    writing_task = Task(
        description=(
            "Using the research provided, write a well-structured article "
            f"about: {topic}\n\n"
            "The article should:\n"
            "- Have a compelling introduction\n"
            "- Present information in a logical flow\n"
            "- Be factual and balanced\n"
            "- Include a brief conclusion\n"
            "- Be written for an informed general audience"
        ),
        expected_output=(
            "A polished, well-written article in markdown format, "
            "ready for publication."
        ),
        agent=writer,
    )

    return Crew(
        agents=[researcher, writer],
        tasks=[research_task, writing_task],
        process=Process.sequential,
        verbose=True,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    """Health check - also verifies Ollama connectivity."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{OLLAMA_HOST}/api/tags")
            models = [m["name"] for m in r.json().get("models", [])]
        return {
            "status": "healthy",
            "ollama": "connected",
            "available_models": models,
            "configured_model": OLLAMA_MODEL,
        }
    except Exception as e:
        return {
            "status": "degraded",
            "ollama": f"unreachable: {str(e)}",
            "hint": "Is your Ollama container on the 'shared-ai' network?",
        }


@app.post("/research", response_model=ResearchResponse)
async def research(request: ResearchRequest):
    """
    Run the research crew on a topic.

    This is what AnythingLLM calls via custom agent skill.
    """
    logger.info(f"Research request: topic='{request.topic}', depth='{request.depth}'")

    start = datetime.now()
    try:
        crew = build_crew(request.topic, request.depth)
        # Run in thread pool since CrewAI is synchronous
        result = await asyncio.to_thread(
            crew.kickoff,
            inputs={"topic": request.topic},
        )
        duration = (datetime.now() - start).total_seconds()

        return ResearchResponse(
            topic=request.topic,
            result=str(result),
            duration_seconds=round(duration, 2),
            model=OLLAMA_MODEL,
            agents_used=["Senior Research Analyst", "Expert Content Writer"],
        )

    except Exception as e:
        logger.error(f"Crew execution failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "hint": (
                    "Check that Ollama is running and the model "
                    f"'{OLLAMA_MODEL}' is pulled."
                ),
            },
        )


@app.get("/models")
async def list_models():
    """List available Ollama models."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{OLLAMA_HOST}/api/tags")
            return r.json()
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


# ---------------------------------------------------------------------------
# Entrypoint for direct run
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

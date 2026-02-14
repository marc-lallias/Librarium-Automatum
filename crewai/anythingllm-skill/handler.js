// AnythingLLM Custom Agent Skill: CrewAI Research
// This handler is called when the agent decides to use the research tool.

module.exports.runtime = {
  handler: async function ({ topic }) {
    const baseUrl =
      this.runtimeArgs?.CREWAI_API_URL || "http://crewai-service:8000";
    const depth = this.runtimeArgs?.RESEARCH_DEPTH || "medium";

    try {
      this.introspect(
        `🔬 Sending research request to CrewAI crew: "${topic}" (depth: ${depth})`
      );

      const response = await fetch(`${baseUrl}/research`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic, depth }),
        signal: AbortSignal.timeout(300000), // 5 min timeout - crews take time
      });

      if (!response.ok) {
        const errBody = await response.text();
        this.introspect(`❌ CrewAI returned error: ${response.status}`);
        return `CrewAI research failed (HTTP ${response.status}): ${errBody}`;
      }

      const data = await response.json();

      this.introspect(
        `✅ Research complete! Took ${data.duration_seconds}s using agents: ${data.agents_used.join(", ")}`
      );

      return data.result;
    } catch (error) {
      this.introspect(`❌ Failed to reach CrewAI service: ${error.message}`);
      return `Error contacting CrewAI service at ${baseUrl}: ${error.message}. Make sure the crewai-service container is running and on the same Docker network.`;
    }
  },
};

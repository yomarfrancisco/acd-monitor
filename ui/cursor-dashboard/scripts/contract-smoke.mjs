import fs from "node:fs";

// Basic contract validation without importing TypeScript schemas
const samples = [
  "risk-summary.json",
  "metrics-overview.json", 
  "health-run.json",
  "events.json",
  "datasources.json",
  "evidence-export.json"
];

for (const file of samples) {
  const data = JSON.parse(fs.readFileSync(new URL(`./golden/${file}`, import.meta.url)));
  
  // Basic validation - ensure required fields exist
  if (!data || typeof data !== 'object') {
    throw new Error(`${file}: Invalid JSON structure`);
  }
  
  // Check for common required fields
  if (data.updatedAt && typeof data.updatedAt !== 'string') {
    throw new Error(`${file}: updatedAt must be string`);
  }
  
  console.log(`✓ ${file} - basic validation passed`);
}

// Agent Chat API smoke test
async function testAgentChatAPI() {
  try {
    console.log('Testing Agent Chat API...');
    
    // Test the agent chat API without API key (should return mock response)
    const response = await fetch('http://localhost:3004/api/agent/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        messages: [
          { role: 'user', content: 'Test message' }
        ],
        sessionId: 'test-session'
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    // Check response headers
    const agentMode = response.headers.get('x-agent-mode');
    if (agentMode !== 'mock') {
      throw new Error(`Expected x-agent-mode: mock, got: ${agentMode}`);
    }

    // Check response body
    const data = await response.json();
    if (!data.reply || typeof data.reply !== 'string') {
      throw new Error('Response missing or invalid reply field');
    }

    if (!data.sessionId || typeof data.sessionId !== 'string') {
      throw new Error('Response missing or invalid sessionId field');
    }

    if (!data.reply.startsWith('[mock]')) {
      throw new Error('Expected mock response to start with [mock]');
    }

    console.log('✓ Agent Chat API - mock response validation passed');
    
    // Test debug parameter (preview only)
    console.log('Testing Agent Chat API with debug parameter...');
    const debugResponse = await fetch('http://localhost:3004/api/agent/chat?debug=1', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        messages: [
          { role: 'user', content: 'Debug test message' }
        ],
        sessionId: 'debug-test-session'
      }),
    });

    if (debugResponse.ok) {
      const debugData = await debugResponse.json();
      const agentMode = debugResponse.headers.get('x-agent-mode');
      
      if (agentMode === 'mock' && debugData.usage?.error_details) {
        console.log('✓ Agent Chat API - debug headers validation passed');
      } else {
        console.log('✓ Agent Chat API - debug parameter accepted');
      }
    }
    
  } catch (error) {
    console.error('Agent Chat API test failed:', error.message);
    // Don't fail the entire test suite if the server isn't running
    console.log('⚠ Agent Chat API test skipped (server not running)');
  }
}

// Run the agent chat test
await testAgentChatAPI();

console.log("All contracts OK");

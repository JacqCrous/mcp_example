### MCP - History

A brief history of the Model Context protocol:

## The Problem: The "Connector Chaos" of 2023
Pre-MCP connecting tools to agents was typically done using LLM routing. The problem with this is scaling and maintainability of the tools as changes to APIs and tools broke agentic workflows or switching between different LLM providers would also break the workflow.

Connecting an AI agent to tools like Jira, Notion, or a company's internal database, one would need to to build a custom, one-off integration. This resulted in a messy, brittle system of "connector chaos." They realized they were spending more time building and maintaining these specific connectors than improving their core AI capabilities.

## The Solution: Anthorpic November 2024:

In late 2024 Anthropic released the Model Context Protocol to standardize how tools are used in agentic workflows. Through the adoption of this standard suddenly tools can be added to agentic workflows at scale while retaining maintainability.

MCP has become the gold standard for adding tools to agentic workflows. It is the preferred way of calling tool over direct tool calling for one primary reason: **standardization**. Direct tool calling is like having a different, proprietary charger for every phone, while MCP is like having one universal standard like USB-C.

This standardization provides several key advantages that make building and scaling AI applications much easier.

---

### The "Proprietary Charger" Problem 🔌

Direct tool calling, like OpenAI's Function Calling or Anthropic's Tool Use, is specific to that provider. If you build a set of tools for OpenAI's model, the way you define those tools and the way the model responds is unique to OpenAI. If you want to switch to a different model provider, you have to rewrite your tool-handling logic. This creates **vendor lock-in**.

MCP solves this by creating an open, universal protocol that separates the AI model from the tools it uses.

---

### Interoperability & Portability 🔄

With MCP, you build your tools once, exposing them through a standard MCP server. Any AI model or agent that "speaks" MCP can then use those tools without any changes.

- **Swap Models Easily:** You can switch from using a Claude model to a Gemini model as your AI's "brain" without rebuilding any of your tools. The new model just points to the same MCP server.
- **Ecosystem of Tools:** It allows for the creation of a universal ecosystem. Anyone can build an MCP-compliant tool (e.g., for Notion or Jira), and it will instantly work with any MCP-compliant AI application.

---

### Simplicity for Tool Developers

When you build a tool using a direct calling method, you have to conform to the specific requirements of that AI provider's API (e.g., defining functions in a specific JSON schema).

With MCP, tool developers are **decoupled** from the AI model. They don't need to know or care which LLM will be using their tool. They simply create a standard MCP server that exposes functions. This makes the developer's job much simpler and allows them to focus on building the tool's core logic, not on compatibility with various AI models.

---

### Enhanced Security & Control 🛡️

Placing your tools behind a dedicated MCP server creates a secure and controlled gateway.

- **Centralized Permissions:** The MCP server can handle authentication, authorization, and logging in one central place. You can define which AI agents are allowed to use which tools.
- **Clear Boundary:** It establishes a clear, auditable boundary between the (potentially unpredictable) AI model and your sensitive internal systems and APIs.

### Summary: MCP vs. Direct Tool Calling

| Feature             | Direct Tool Calling                                                         | Model Context Protocol (MCP)                                        |
| :------------------ | :-------------------------------------------------------------------------- | :------------------------------------------------------------------ |
| **Standardization** | **Proprietary**; specific to each model provider (OpenAI, Anthropic, etc.). | **Open Standard**; works with any compliant model or agent.         |
| **Portability**     | **Low**; tools are tightly coupled to one provider's API.                   | **High**; tools are decoupled and work across any MCP-compliant AI. |
| **Developer Focus** | Must learn and conform to a specific provider's format (e.g., JSON schema). | Focuses on tool logic; exposes it via a universal protocol.         |
| **Security**        | Handled within the application logic, can be complex to manage.             | Centralized at the MCP server, providing a clear, secure gateway.   |


### What this looks like:

Think of it as a structured, predictable conversation. I'll show you a simplified, high-level example of what those messages look like for the calculator example we've been using. This all happens "under the hood" of the Python libraries.

-----

### The Conversation: Client & Server

Here's the step-by-step message exchange that happens over a transport like WebSockets.

**Client**: "Hello, what can you do?"

**Server**: "Here are my capabilities."

**Client**: "Okay, please use your 'add' tool with these numbers."

**Server**: "Here is the result."

Let's see what that looks like in the MCP standard.

-----

### Step 1: The Client Asks What Tools Are Available (Discovery)

The AI client connects and sends a **discovery request** to learn about the server's capabilities.

```json
{
  "type": "discovery_request",
  "id": "req-abc-123"
}
```

-----

### Step 2: The Server Responds with its Tools

The server replies with a **discovery response**, which is like a menu of its available tools. It describes each tool, what it does, and what parameters (arguments) it needs. This "schema" is crucial for the AI to understand how to use the tool correctly.

```json
{
  "type": "discovery_response",
  "id": "req-abc-123",
  "tools": [
    {
      "name": "add",
      "description": "Adds two numbers and returns the result.",
      "parameters": {
        "type": "object",
        "properties": {
          "a": { "type": "integer", "description": "The first number." },
          "b": { "type": "integer", "description": "The second number." }
        },
        "required": ["a", "b"]
      }
    }
  ]
}
```

-----

### Step 3: The Client Calls a Specific Tool

After seeing the menu, the AI decides to use the `add` tool. It sends a **tool call request** with the specific arguments it wants to use.

```json
{
  "type": "tool_call_request",
  "id": "req-xyz-789",
  "tool_name": "add",
  "parameters": {
    "a": 10,
    "b": 32
  }
}
```

-----

### Step 4: The Server Executes the Tool and Returns the Result

The server receives the request, runs its internal Python function `add(10, 32)`, gets the result, and sends back a **tool call response** containing the answer.

```json
{
  "type": "tool_call_response",
  "id": "req-xyz-789",
  "result": 42
}
```

This structured, back-and-forth exchange is the core of the protocol. By standardizing these message formats, any client and any server that follow these rules can communicate effectively without needing to know the specific details of each other's internal code.
"""
FastMCP quickstart example.

cd to the `examples/snippets/clients` directory and run:
    uv run server fastmcp_quickstart stdio
"""

import logging

import ollama
from mcp.server.fastmcp import FastMCP

# Create an MCP server
mcp = FastMCP("Calculator Server")


# Add an addition tool
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b


@mcp.tool()
def math_web_search(query: str) -> str:
    """Search the web for information about math"""
    try:
        response = ollama.chat(
            model="qwen3:1.7b",
            messages=[{"role": "user", "content": query}],
        )
        return response["message"]["content"]
    except Exception as e:
        # Log the error for debugging
        logging.exception(f"Ollama API call failed: {e}")
        # Return a helpful error message to the client
        return "Sorry, the web search is currently unavailable."


# Add a dynamic greeting resource
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting"""
    return f"Hello, {name}!"


# Add a prompt
@mcp.prompt()
def get_greeting_prompt(name: str, style: str = "friendly") -> str:
    """Generate a greeting prompt"""
    styles = {
        "friendly": "Please write a warm, friendly greeting",
        "formal": "Please write a formal, professional greeting",
        "casual": "Please write a casual, relaxed greeting",
    }

    return f"{styles.get(style, styles['friendly'])} for someone named {name}."


@mcp.prompt()
def math_web_search_prompt():
    """Generate helper prompt for web search."""
    return "You are pretending to be a search engine. Answer the query presented with an answer about mathematics."


# 4. Run the server when the script is executed
if __name__ == "__main__":
    logging.info("Starting Server")
    mcp.run(transport="stdio")

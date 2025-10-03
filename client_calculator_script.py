import asyncio
import json
import logging
import sys
from contextlib import AsyncExitStack
from typing import Any

import ollama
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Load environment variables from a .env file if it exists
load_dotenv()


class MCPClient:
    """
    An asynchronous client for interacting with an MCP server, using Ollama for language model capabilities.
    """

    def __init__(self, model: str = "gpt-oss:20b"):
        """
        Initializes the MCPClient.

        Args:
            model: The name of the Ollama model to use for chat completions.
        """
        self.model = model
        self.session: ClientSession | None = None
        self.exit_stack = AsyncExitStack()
        logging.info(f"MCP Client initialized to use Ollama model: '{self.model}'")

    async def connect_to_server(self, server_script_path: str):
        """
        Connects to an MCP server by launching it as a subprocess.

        Args:
            server_script_path: Path to the server script (.py or .js).
        """
        is_python = server_script_path.endswith(".py")
        is_js = server_script_path.endswith(".js")
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None,
        )

        logging.info(f"Starting server: '{command} {server_script_path}'")
        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params),
        )
        stdio, write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(stdio, write),
        )

        await self.session.initialize()

        response = await self.session.list_tools()
        tools = response.tools
        tool_names = [tool.name for tool in tools]
        logging.info(f"\n✅ Connected to server with tools: {tool_names}")

    async def process_query(self, query: str) -> str:
        """
        Processes a user query by interacting with the Ollama model and calling tools via MCP if needed.

        This method handles the full conversation cycle:
        1. Sends the query to Ollama with a list of available tools.
        2. If the model responds with a text message, returns it directly.
        3. If the model responds with tool calls, it executes them via the MCP session.
        4. It then sends the tool results back to the model to get a final summary.

        Args:
            query: The user's query string.

        Returns:
            The final, user-facing response from the language model.
        """
        if not self.session:
            return "Error: Not connected to a server."

        # Initial conversation history
        messages: list[dict[str, Any]] = [{"role": "user", "content": query}]

        # Get available tools from the MCP session
        list_tools_response = await self.session.list_tools()
        available_tools = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": {
                        "type": "object",
                        "properties": tool.inputSchema.get("properties", {}),
                        "required": tool.inputSchema.get("required", []),
                    },
                },
            }
            for tool in list_tools_response.tools
        ]

        # First call to Ollama to determine if a tool is needed
        logging.info(f"Sending initial query to Ollama: '{query}'")
        response = ollama.chat(
            model=self.model,
            messages=messages,
            tools=available_tools,
        )

        response_message = response["message"]
        messages.append(response_message)
        logging.debug(f"Initial Ollama response: {response_message}")

        # Check if the model decided to call any tools
        if not response_message.get("tool_calls"):
            # No tool calls, just return the text content
            logging.info("Ollama provided a direct text response.")
            return response_message.get("content", "Sorry, I received no content.")

        # The model wants to use tools, so execute them
        logging.info("Ollama requested tool calls. Executing now.")
        tool_outputs = []

        for tool_call in response_message["tool_calls"]:
            tool_name = tool_call["function"]["name"]
            tool_args = tool_call["function"]["arguments"]
            logging.info(f"↪ Calling tool '{tool_name}' with args: {tool_args}")

            try:
                result = await self.session.call_tool(tool_name, tool_args)
                # Convert content to string if it's a complex object for the LLM
                content_str = (
                    json.dumps(result.content)
                    if isinstance(result.content, (dict, list))
                    else str(result.content)
                )
                tool_outputs.append(f"[Tool '{tool_name}' returned: {content_str}]")

                # Append the tool's result to the conversation history for the next turn
                messages.append(
                    {
                        "role": "tool",
                        "content": content_str,
                    },
                )
            except Exception as e:
                error_message = f"Error calling tool '{tool_name}': {e}"
                logging.exception(error_message)
                tool_outputs.append(f"[{error_message}]")
                messages.append(
                    {
                        "role": "tool",
                        "content": error_message,
                    },
                )

        logging.info("✨ Tools executed. Asking model to summarize the results...")
        logging.info("Sending tool results back to Ollama for final response.")

        # Second call to Ollama to get a natural language response based on tool results
        final_response = ollama.chat(
            model=self.model,
            messages=messages,
            # No 'tools' argument here, as we expect a text-only summary
        )

        final_message = final_response["message"]["content"]
        logging.debug(f"Final Ollama response: {final_message}")

        # Combine the procedural text with the final answer for a complete view
        user_facing_output = "\n".join(tool_outputs) + "\n\n" + final_message
        return user_facing_output

    async def chat_loop(self):
        """Runs an interactive chat loop in the console."""
        ("\n🤖 MCP Client Started!")
        logging.info("Type your queries below or enter 'quit' to exit.")

        while True:
            try:
                query = input("\n> ").strip()
                if query.lower() == "quit":
                    logging.info("Exiting client. Goodbye!")
                    break
                if not query:
                    continue

                response = await self.process_query(query)
                logging.info(f"\n{response}")

            except (EOFError, KeyboardInterrupt):
                logging.info("\nExiting client. Goodbye!")
                break
            except Exception as e:
                logging.error(
                    f"An unexpected error occurred in the chat loop: {e}",
                    exc_info=True,
                )
                logging.exception(f"\nAn error occurred: {e}")

    async def cleanup(self):
        """Cleans up all managed resources, like the server process."""
        logging.info("Cleaning up resources and shutting down.")
        await self.exit_stack.aclose()


async def main():
    """Main entry point for the client application."""
    # Set up basic logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    if len(sys.argv) < 2:
        logging.info("Usage: python client.py <path_to_server_script.py|js>")
        sys.exit(1)

    client = MCPClient(model="gpt-oss:20b")  # You can change the default model here
    try:
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

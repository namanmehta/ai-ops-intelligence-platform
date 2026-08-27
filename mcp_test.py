import os
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

host = os.getenv("DATABRICKS_SERVER_HOSTNAME")
token = os.getenv("DATABRICKS_ACCESS_TOKEN")

mcp_url = f"https://adb-7405617340079921.1.azuredatabricks.net/api/2.0/mcp/ai-search/ai_ops_platform/bronze/doc_index_2"

response = client.beta.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=1000,
    messages=[
        {"role": "user", "content": "Search this documentation source for our policy on schema changes."}
    ],
    mcp_servers=[
        {
            "type": "url",
            "url": mcp_url,
            "name": "databricks-docs",
            "authorization_token": token,
        }
    ],
    tools=[{"type": "mcp_toolset", "mcp_server_name": "databricks-docs"}],
    betas=["mcp-client-2025-11-20"],
)

for block in response.content:
    print(block)
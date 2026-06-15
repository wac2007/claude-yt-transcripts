# yt-summarizer

An MCP server that fetches YouTube transcripts and saves summaries to a local folder or Notion.

## Tools

| Tool | Description |
|---|---|
| `get_transcript` | Fetch a video transcript (checks local cache first) |
| `save_transcription` | Save a transcript/summary to a local `.md` file or Notion |
| `delete_transcript` | Delete a locally cached transcript |
| `create_notion_page` | Create a Notion page directly |

## Environment variables

Copy `.env.example` to `.env` and fill in the values:

```env
# Set to "false" to save transcripts as local .md files instead
USE_NOTION=true

# Folder for local transcript files (used when USE_NOTION=false)
TRANSCRIPTS_FOLDER=transcripts

# Required when USE_NOTION=true
NOTION_TOKEN=secret_...
PARENT_PAGE_ID=<notion-page-id>
```

## Install

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync
```

## Development

Run the server locally with the MCP inspector:

```bash
uv run mcp dev server.py
```

## Adding to Claude Code

```bash
claude mcp add yt-summarizer -- uv --directory /path/to/yt-summarizer run server.py
```

Then set environment variables:

```bash
claude mcp add yt-summarizer \
  -e USE_NOTION=false \
  -e TRANSCRIPTS_FOLDER=/path/to/transcripts \
  -- uv --directory /path/to/yt-summarizer run server.py
```

## Adding to Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "yt-summarizer": {
      "command": "uv",
      "args": [
        "--directory", "/path/to/yt-summarizer",
        "run", "server.py"
      ],
      "env": {
        "USE_NOTION": "false",
        "TRANSCRIPTS_FOLDER": "/path/to/transcripts",
        "NOTION_TOKEN": "secret_...",
        "PARENT_PAGE_ID": "your-page-id"
      }
    }
  }
}
```

Restart Claude Desktop after editing the config.

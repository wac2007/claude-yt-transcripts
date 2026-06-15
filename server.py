from mcp.server.fastmcp import FastMCP
from youtube_transcript_api import YouTubeTranscriptApi
import requests
from typing import Dict, Any, Optional
import os
import datetime
from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
PARENT_PAGE_ID = os.getenv("PARENT_PAGE_ID")
USE_NOTION = os.getenv("USE_NOTION", "true").lower() == "true"
TRANSCRIPTS_FOLDER = os.getenv("TRANSCRIPTS_FOLDER", "transcripts")

mcp = FastMCP("Youtube Summarizer")

ytt_api = YouTubeTranscriptApi()

# Set up the headers for the request
headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def _local_transcript_path(video_id: str) -> str:
    """Returns the expected local file path for a given video_id."""
    safe_id = "".join(c if c.isalnum() or c in " -_" else "_" for c in video_id).strip()
    return os.path.join(TRANSCRIPTS_FOLDER, f"{safe_id}.md")


def _extract_transcript_from_md(content: str) -> str:
    """Extract just the transcript text from a markdown file with frontmatter."""
    marker = "## Transcript\n\n"
    idx = content.find(marker)
    if idx != -1:
        return content[idx + len(marker):]
    # Fallback: strip YAML frontmatter if transcript section not found
    if content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            return content[end + 3:].lstrip()
    return content

@mcp.tool()
def get_transcript(video_id: str) -> str:
    """
    Fetches the transcript of a YouTube video.
    Checks for a locally saved transcript first before calling the YouTube API.
    Args:
        video_id: The ID of the YouTube video.
    Returns:
        The transcript of the YouTube video.
    """
    local_path = _local_transcript_path(video_id)
    if os.path.exists(local_path):
        with open(local_path, "r", encoding="utf-8") as f:
            content = f.read()
        return _extract_transcript_from_md(content)

    fetched_transcript = ytt_api.fetch(video_id)
    transcript_text = ""
    for snippet in fetched_transcript:
        transcript_text += snippet.text + " "
    if not USE_NOTION:
        save_transcript_to_file(video_id, transcript_text)
    return transcript_text

@mcp.tool()
def delete_transcript(video_id: str) -> str:
    """
    Deletes the locally saved transcript file for a YouTube video.
    Args:
        video_id: The ID of the YouTube video whose transcript should be removed.
    Returns:
        A message indicating whether the file was deleted or did not exist.
    """
    local_path = _local_transcript_path(video_id)
    if not os.path.exists(local_path):
        return f"No local transcript found for video '{video_id}'."
    os.remove(local_path)
    return f"Transcript for '{video_id}' deleted from {local_path}."

@mcp.tool()
def create_notion_page(notion_page_content: Dict[str, Any]):    
    """
    Creates a new page in Notion with a fully structured page with all the information from the video transcript. Make sure to include "parent": {"page_id": PARENT_PAGE_ID}, in the dictionary.
    Args:
        notion_page_content: A dictionary containing the content of the new page.
        Sample Structure:
        {
            "parent": {"page_id": PARENT_PAGE_ID},
            "properties": {
                "title": {
                    "title": [
                        {
                            "text": {
                                "content": "New Page Title"
                            }
                        }
                    ]
                }
            },
            "children": [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": "This is a paragraph in the new page."
                                }
                            }
                        ]
                    }
                },
                {
                    "object": "block",
                    "type": "to_do",
                    "to_do": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": "This is a to-do item."
                                }
                            }
                        ],
                        "checked": False
                    }
                }
            ]
        }
    Returns:
        The response from the Notion API.
    """
    notion_page_content["parent"]["page_id"] = PARENT_PAGE_ID
    response = requests.post("https://api.notion.com/v1/pages", headers=headers, json=notion_page_content)
    return response.text

def save_transcript_to_file(
    video_id: str,
    content: str,
    title: str = "",
    description: str = "",
    yt_description: str = "",
) -> str:
    """Saves transcript content to a .md file with YAML frontmatter in TRANSCRIPTS_FOLDER."""
    os.makedirs(TRANSCRIPTS_FOLDER, exist_ok=True)
    file_path = _local_transcript_path(video_id)
    display_title = title or video_id
    date_str = datetime.date.today().isoformat()

    frontmatter_lines = [
        "---",
        f'title: "{display_title}"',
        f'video_id: "{video_id}"',
        f'date: "{date_str}"',
    ]
    if description:
        safe_desc = description.replace('"', '\\"')
        frontmatter_lines.append(f'description: "{safe_desc}"')
    frontmatter_lines.append("---")

    body_sections = []
    if yt_description:
        body_sections.append(f"## YouTube Description\n\n{yt_description}")
    body_sections.append(f"## Transcript\n\n{content}")

    file_content = "\n".join(frontmatter_lines) + "\n\n" + "\n\n".join(body_sections) + "\n"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(file_content)
    return f"Transcript saved to {file_path}"

@mcp.tool()
def save_transcription(
    video_id: str,
    content: str,
    title: str = "",
    description: str = "",
    yt_description: str = "",
    notion_page_content: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Saves a transcription either to a local .md file or to Notion, depending on the USE_NOTION env variable.
    When USE_NOTION is false, saves a markdown file with frontmatter to TRANSCRIPTS_FOLDER.
    When USE_NOTION is true, creates a Notion page using notion_page_content.
    Args:
        video_id: The YouTube video ID (used as filename key and in frontmatter).
        content: The plain-text transcript content.
        title: Human-readable video title for frontmatter (defaults to video_id if omitted).
        description: Short description of the video for frontmatter (1-2 sentences, aids future search).
        yt_description: Full YouTube video description to include in the file body (optional).
        notion_page_content: Required when USE_NOTION is true. A Notion page dict (same format as create_notion_page).
    Returns:
        A message describing where the transcription was saved.
    """
    if not USE_NOTION:
        return save_transcript_to_file(video_id, content, title=title, description=description, yt_description=yt_description)

    if not notion_page_content:
        return "Error: notion_page_content is required when USE_NOTION is true."
    notion_page_content["parent"]["page_id"] = PARENT_PAGE_ID
    response = requests.post("https://api.notion.com/v1/pages", headers=headers, json=notion_page_content)
    return response.text

if __name__ == "__main__":
    mcp.run()

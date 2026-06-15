from mcp.server.fastmcp import FastMCP
from youtube_transcript_api import YouTubeTranscriptApi
import requests
from typing import Dict, Any
import os
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
    safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in video_id).strip()
    return os.path.join(TRANSCRIPTS_FOLDER, f"{safe_title}.txt")

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
        # Strip the "video_id\n\n" header written by save_transcript_to_file
        prefix = f"{video_id}\n\n"
        return content[len(prefix):] if content.startswith(prefix) else content

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

def save_transcript_to_file(title: str, content: str) -> str:
    """Saves transcript content to a .txt file in TRANSCRIPTS_FOLDER."""
    os.makedirs(TRANSCRIPTS_FOLDER, exist_ok=True)
    safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in title).strip()
    file_path = os.path.join(TRANSCRIPTS_FOLDER, f"{safe_title}.txt")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"{title}\n\n{content}")
    return f"Transcript saved to {file_path}"

@mcp.tool()
def save_transcription(title: str, content: str, notion_page_content: Dict[str, Any] = None) -> str:
    """
    Saves a transcription either to a local file or to Notion, depending on the USE_NOTION env variable.
    When USE_NOTION is false, saves a .txt file to the TRANSCRIPTS_FOLDER directory.
    When USE_NOTION is true, creates a Notion page using notion_page_content.
    Args:
        title: The title of the transcription (used as filename when saving to file).
        content: The plain-text transcript content.
        notion_page_content: Required when USE_NOTION is true. A Notion page dict (same format as create_notion_page).
    Returns:
        A message describing where the transcription was saved.
    """
    if not USE_NOTION:
        return save_transcript_to_file(title, content)

    if not notion_page_content:
        return "Error: notion_page_content is required when USE_NOTION is true."
    notion_page_content["parent"]["page_id"] = PARENT_PAGE_ID
    response = requests.post("https://api.notion.com/v1/pages", headers=headers, json=notion_page_content)
    return response.text

if __name__ == "__main__":
    mcp.run()

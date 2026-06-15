from mcp.server.fastmcp import FastMCP
from youtube_transcript_api import YouTubeTranscriptApi
import requests
from typing import Dict, Any
import os
from dotenv import load_dotenv 

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
PARENT_PAGE_ID = os.getenv("PARENT_PAGE_ID")

mcp = FastMCP("Youtube Summarizer")

ytt_api = YouTubeTranscriptApi()

# Set up the headers for the request
headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

@mcp.tool()
def get_transcript(video_id: str) -> str:
    """
    Fetches the transcript of a YouTube video.
    Args:
        video_id: The ID of the YouTube video.
    Returns:
        The transcript of the YouTube video.
    """
    fetched_transcript = ytt_api.fetch(video_id)
    transcript_text = ""
    for snippet in fetched_transcript:
        transcript_text += snippet.text + " "
    return transcript_text

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
    response = requests.post(f"<https://api.notion.com/v1/pages>", headers=headers, json=notion_page_content)
    return response.text

if __name__ == "__main__":
    mcp.run()

"""
parsers/parse_messages.py — Parses LinkedIn message inbox (full threads).

LinkedIn exports messages as a flat CSV where each row is one message.
We reconstruct full conversation threads by grouping on CONVERSATION ID,
then store each thread as one or more DocumentChunks.

Columns: CONVERSATION ID, CONVERSATION TITLE, FROM, SENDER PROFILE URL,
         TO, RECIPIENT PROFILE URLS, DATE, SUBJECT, CONTENT, FOLDER, ATTACHMENTS
"""

import csv
from pathlib import Path
from collections import defaultdict
from utils.schema import DocumentChunk
from config import CSV


def _read_messages_csv() -> list[dict]:
    path = CSV["messages"]
    if not path.exists():
        print(f"[parse_messages] Warning: {path} not found.")
        return []
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _format_thread(messages: list[dict]) -> str:
    """
    Format a list of messages (sorted oldest first) into a readable thread string.
    """
    lines = []
    for msg in messages:
        sender  = msg.get("FROM", "").strip()
        date    = msg.get("DATE", "").strip()
        content = msg.get("CONTENT", "").strip()
        if not content:
            continue
        header = f"[{date}] {sender}:" if date else f"{sender}:"
        lines.append(f"{header}\n{content}")
    return "\n\n".join(lines)


def parse_messages() -> list[DocumentChunk]:
    rows = _read_messages_csv()
    if not rows:
        return []

    # Group messages by conversation
    threads: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        conv_id = row.get("CONVERSATION ID", "").strip()
        if conv_id:
            threads[conv_id].append(row)

    chunks = []
    for conv_id, messages in threads.items():
        # Sort by date ascending (oldest first)
        messages.sort(key=lambda r: r.get("DATE", ""))

        title = messages[0].get("CONVERSATION TITLE", "").strip() or \
                messages[0].get("SUBJECT", "").strip() or \
                f"Conversation {conv_id}"

        # Identify participants
        participants = set()
        for msg in messages:
            sender = msg.get("FROM", "").strip()
            if sender:
                participants.add(sender)

        thread_text = _format_thread(messages)
        if not thread_text:
            continue

        # Date range of conversation
        dates = [m.get("DATE", "") for m in messages if m.get("DATE", "")]
        date_from = min(dates) if dates else None
        date_to   = max(dates) if dates else None

        # Other participants (everyone except self — identified as the non-repeated sender)
        # We store all participants in metadata; the LLM can sort it out
        participant_str = ", ".join(sorted(participants))

        document = (
            f"Conversation: {title}\n"
            f"Participants: {participant_str}\n"
            f"Messages ({len(messages)} total):\n\n"
            f"{thread_text}"
        )

        chunks.append(DocumentChunk(
            document=document,
            collection="communications",
            source="csv",
            type="message_thread",
            entity_id=f"conversation::{conv_id}",
            entity_name=title,
            date_from=date_from,
            date_to=date_to,
            extra={
                "message_count": str(len(messages)),
                "participants": participant_str,
                "conv_id": conv_id,
            },
        ))

    print(f"[parse_messages] {len(chunks)} conversation thread chunks from {len(rows)} messages.")
    return chunks

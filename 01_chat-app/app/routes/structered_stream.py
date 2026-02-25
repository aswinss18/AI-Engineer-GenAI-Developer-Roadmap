# main.py

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from openai import OpenAI
import os

router = APIRouter()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


@router.post("/structured_stream")
async def structured_stream_response(prompt: str):
    try:
        stream = client.responses.stream(
            model="gpt-4.1",
            input=prompt,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "summary_schema",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "summary": {"type": "string"},
                            "confidence": {"type": "number"}
                        },
                        "required": ["summary", "confidence"]
                    }
                }
            }
        )
    except TypeError:
        # Fallback for SDKs that don't accept `response_format`
        stream = client.responses.stream(model="gpt-4.1", input=prompt)

    async def generator():
        try:
            def to_sse_bytes(chunk):
                if isinstance(chunk, bytes):
                    s = chunk.decode("utf-8", errors="replace")
                else:
                    s = str(chunk)
                # Prefix every line with 'data: ' per SSE spec
                s = s.replace("\r\n", "\n").replace("\n", "\n")
                s = s.replace("\n", "\ndata: ")
                payload = f"data: {s}\n\n"
                return payload.encode("utf-8")

            if hasattr(stream, "__aiter__"):
                async for event in stream:
                    if hasattr(event, "delta"):
                        chunk = event.delta
                    elif hasattr(event, "text"):
                        chunk = event.text
                    else:
                        chunk = str(event)

                    if chunk is None:
                        continue
                    yield to_sse_bytes(chunk)
            elif hasattr(stream, "__iter__"):
                for event in stream:
                    if hasattr(event, "delta"):
                        chunk = event.delta
                    elif hasattr(event, "text"):
                        chunk = event.text
                    else:
                        chunk = str(event)

                    if chunk is None:
                        continue
                    yield to_sse_bytes(chunk)
            else:
                # Try to access a mangled internal stream attribute
                inner = getattr(stream, "_ResponseStreamManager__stream", None)
                if inner is not None:
                    if hasattr(inner, "__aiter__"):
                        async for event in inner:
                            if hasattr(event, "delta"):
                                chunk = event.delta
                            elif hasattr(event, "text"):
                                chunk = event.text
                            else:
                                chunk = str(event)
                            if chunk is None:
                                continue
                            yield to_sse_bytes(chunk)
                    elif hasattr(inner, "__iter__"):
                        for event in inner:
                            if hasattr(event, "delta"):
                                chunk = event.delta
                            elif hasattr(event, "text"):
                                chunk = event.text
                            else:
                                chunk = str(event)
                            if chunk is None:
                                continue
                            yield to_sse_bytes(chunk)
                    else:
                        yield to_sse_bytes(str(inner))
                else:
                    # As a final fallback, call the chat completions endpoint
                    # to verify the backend and API key, and yield that text.
                    try:
                        resp = client.chat.completions.create(
                            model="gpt-4o-mini",
                            temperature=0.3,
                            messages=[
                                {"role": "system", "content": "You are concise."},
                                {"role": "user", "content": prompt},
                            ],
                        )
                        content = None
                        try:
                            content = resp.choices[0].message.content
                        except Exception:
                            content = str(resp)
                        yield to_sse_bytes(content)
                    except Exception as e:
                        try:
                            entries = sorted(dir(stream))
                            yield to_sse_bytes("\n".join(entries))
                        except Exception:
                            yield to_sse_bytes("FALLBACK ERROR: " + str(e))
        finally:
            try:
                # attempt async close if available
                if hasattr(stream, "aclose"):
                    await stream.aclose()
                elif hasattr(stream, "close"):
                    stream.close()
            except Exception:
                pass

    return StreamingResponse(generator(), media_type="text/event-stream")
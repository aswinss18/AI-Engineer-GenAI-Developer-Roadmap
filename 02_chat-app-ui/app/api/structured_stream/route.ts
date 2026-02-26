/**
 * Next.js API route to proxy structured streaming requests to the backend.
 */

export async function POST(request: Request) {
  // read JSON body for prompt (and optional temperature/mode if you decide to support them)
  const body = await request.json();
  const prompt = body.prompt as string;

  if (!prompt) {
    return new Response("Missing 'prompt' parameter", { status: 400 });
  }

  try {
    const backendUrl = `http://localhost:8000/structured_stream?prompt=${encodeURIComponent(
      prompt
    )}`;

    const response = await fetch(backendUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      return new Response("Backend error", { status: response.status });
    }

    // Stream the response body directly to the client
    return new Response(response.body, {
      status: 200,
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
      },
    });
  } catch (error) {
    console.error("Structured Stream API error:", error);
    return new Response("Internal Server Error", { status: 500 });
  }
}

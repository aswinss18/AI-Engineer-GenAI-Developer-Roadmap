/**
 * Next.js API route to proxy streaming requests to the backend.
 */

export async function POST(request: Request) {
  // read JSON body for message, temperature and mode
  const body = await request.json();
  const message = body.message as string;
  const temperature = body.temperature ?? 0.2;
  const mode = body.mode ?? "default";

  if (!message) {
    return new Response("Missing 'message' parameter", { status: 400 });
  }

  try {
    const backendUrl = `http://localhost:8000/stream?message=${encodeURIComponent(
      message
    )}&temperature=${encodeURIComponent(String(temperature))}&mode=${encodeURIComponent(
      mode
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
    console.error("Stream API error:", error);
    return new Response("Internal Server Error", { status: 500 });
  }
}

/**
 * Next.js API route to proxy streaming requests to the backend.
 */

export async function POST(request: Request) {
  const { searchParams } = new URL(request.url);
  const message = searchParams.get("message");

  if (!message) {
    return new Response("Missing 'message' parameter", { status: 400 });
  }

  try {
    const backendUrl = `http://localhost:8000/stream?message=${encodeURIComponent(
      message
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

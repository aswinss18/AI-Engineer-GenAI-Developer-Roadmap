/**
 * Next.js API route for regular (non-streaming) chat.
 */

export async function POST(request: Request) {
  const { searchParams } = new URL(request.url);
  const message = searchParams.get("message");

  if (!message) {
    return new Response(JSON.stringify({ error: "Missing 'message' parameter" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  try {
    const backendUrl = `http://localhost:8000/chat?message=${encodeURIComponent(
      message
    )}`;

    const response = await fetch(backendUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      return new Response(JSON.stringify({ error: "Backend error" }), {
        status: response.status,
        headers: { "Content-Type": "application/json" },
      });
    }

    const data = await response.json();
    return new Response(JSON.stringify(data), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  } catch (error) {
    console.error("Chat API error:", error);
    return new Response(
      JSON.stringify({ error: "Internal Server Error" }),
      {
        status: 500,
        headers: { "Content-Type": "application/json" },
      }
    );
  }
}

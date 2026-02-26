/**
 * Next.js API route for regular (non-streaming) chat.
 */

export async function POST(request: Request) {
  // expect JSON body: { message, temperature?, mode? }
  const body = await request.json();
  const message = body.message as string;
  const temperature = body.temperature ?? 0.3;
  const mode = body.mode ?? "default";
  const deterministic = body.deterministic ?? false;

  if (!message) {
    return new Response(JSON.stringify({ error: "Missing 'message' parameter" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  try {
    // forward parameters as query params so backend routes (fastapi) pick them up
    const backendUrl = `http://localhost:8000/chat?message=${encodeURIComponent(
      message
    )}&temperature=${encodeURIComponent(String(temperature))}&mode=${encodeURIComponent(
      mode
    )}&deterministic=${encodeURIComponent(String(deterministic))}`;

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

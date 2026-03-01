/**
 * Next.js API route to proxy queries to the FAISS search backend.
 *
 * By default the backend is assumed to be running at localhost:8001, but can be
 * overridden with the SEARCH_BACKEND_URL environment variable (eg. "http://localhost:8000").
 *
 * The body is expected to be JSON { query: string } and the response from the
 * backend is returned verbatim so the client can render the results.
 */

const DEFAULT_BACKEND = "http://localhost:8001";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const query = body.query as string;
    if (!query) {
      return new Response(JSON.stringify({ error: "Missing 'query' parameter" }), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      });
    }

    const backendUrl = `${process.env.SEARCH_BACKEND_URL ?? DEFAULT_BACKEND}/search?query=${encodeURIComponent(
      query
    )}`;

    const response = await fetch(backendUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });

    if (!response.ok) {
      return new Response(JSON.stringify({ error: "Search backend error" }), {
        status: response.status,
        headers: { "Content-Type": "application/json" },
      });
    }

    const data = await response.json();
    return new Response(JSON.stringify(data), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  } catch (err) {
    console.error("Search proxy error", err);
    return new Response(JSON.stringify({ error: "Internal Server Error" }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }
}

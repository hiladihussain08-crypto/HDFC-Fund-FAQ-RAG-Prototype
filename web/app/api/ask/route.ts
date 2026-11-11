import { NextRequest, NextResponse } from "next/server";

export const maxDuration = 90;

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";
const API_KEY = process.env.API_KEY || "";

export async function POST(req: NextRequest) {
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body." }, { status: 400 });
  }

  const question = (body as { question?: unknown })?.question;
  if (typeof question !== "string" || question.trim().length === 0) {
    return NextResponse.json({ error: "Question must be a non-empty string." }, { status: 400 });
  }
  if (question.length > 300) {
    return NextResponse.json({ error: "Question must be 300 characters or fewer." }, { status: 400 });
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 70000);

  try {
    const res = await fetch(`${BACKEND_URL}/ask`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY,
      },
      body: JSON.stringify({ question }),
      signal: controller.signal,
    });
    clearTimeout(timeout);

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const msg =
        (data && (data.detail || data.error)) ||
        "The service returned an error. Please try again.";
      return NextResponse.json({ error: String(msg) }, { status: res.status });
    }
    return NextResponse.json(data, { status: 200 });
  } catch (err) {
    clearTimeout(timeout);
    const isAbort = err instanceof Error && err.name === "AbortError";
    const msg = isAbort
      ? "The request took too long. Please try again."
      : "Could not reach the backend. Please try again.";
    return NextResponse.json({ error: msg }, { status: 502 });
  }
}

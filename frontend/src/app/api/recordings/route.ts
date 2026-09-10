import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

import { NextResponse } from "next/server";

export const runtime = "nodejs";

function safeRecordingId(raw: string): string {
  const cleaned = raw.replace(/[^a-zA-Z0-9._-]/g, "_").slice(0, 80);
  return cleaned || `rec-${Date.now()}`;
}

export async function POST(request: Request): Promise<NextResponse> {
  const form = await request.formData();
  const file = form.get("file");
  const rawId = form.get("id");
  if (!(file instanceof File) || file.size === 0) {
    return NextResponse.json({ error: "arquivo de áudio vazio" }, { status: 400 });
  }
  const recordingId = safeRecordingId(
    typeof rawId === "string" ? rawId : `rec-${Date.now()}`,
  );
  const directory = path.join(process.cwd(), "recordings");
  await mkdir(directory, { recursive: true });
  const buffer = Buffer.from(await file.arrayBuffer());
  const ext = path.extname(file.name) || ".webm";
  const filename = `${recordingId}${ext}`;
  await writeFile(path.join(directory, filename), buffer);
  return NextResponse.json({ saved: filename });
}

"use client";

import { useState } from "react";
import ModeSelector from "./components/ModeSelector";
import ChatWindow from "./components/ChatWindow";

type Mode = "normal" | "stream" | "structured" | "search";

export default function Home() {
  const [mode, setMode] = useState<Mode | null>(null);

  if (!mode) {
    return <ModeSelector onSelect={(m) => setMode(m)} />;
  }

  return <ChatWindow mode={mode} onBack={() => setMode(null)} />;
}

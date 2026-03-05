"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import ModeSelector from "./components/ModeSelector";
import ChatWindow from "./components/ChatWindow";

type Mode = "normal" | "stream" | "structured" | "search" | "document" | "similarity" | "semantic-search" | "pdf-rag";

export default function Home() {
  const [mode, setMode] = useState<Mode | null>(null);
  const router = useRouter();

  const handleModeSelect = (selectedMode: Mode) => {
    if (selectedMode === "similarity") {
      router.push("/similarity");
    } else if (selectedMode === "semantic-search") {
      router.push("/semantic-search");
    } else if (selectedMode === "pdf-rag") {
      router.push("/pdf-rag");
    } else {
      setMode(selectedMode);
    }
  };

  if (!mode) {
    return <ModeSelector onSelect={handleModeSelect} />;
  }

  return <ChatWindow mode={mode} onBack={() => setMode(null)} />;
}

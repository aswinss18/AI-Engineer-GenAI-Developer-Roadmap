"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import ModeSelector from "./components/ModeSelector";
import ChatWindow from "./components/ChatWindow";

type Mode = "normal" | "stream" | "structured" | "search" | "document" | "similarity";

export default function Home() {
  const [mode, setMode] = useState<Mode | null>(null);
  const router = useRouter();

  const handleModeSelect = (selectedMode: Mode) => {
    if (selectedMode === "similarity") {
      router.push("/similarity");
    } else {
      setMode(selectedMode);
    }
  };

  if (!mode) {
    return <ModeSelector onSelect={handleModeSelect} />;
  }

  return <ChatWindow mode={mode} onBack={() => setMode(null)} />;
}

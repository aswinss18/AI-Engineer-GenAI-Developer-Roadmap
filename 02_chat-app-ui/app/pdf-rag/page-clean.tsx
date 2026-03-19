"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";

interface Message {
    role: "user" | "ai";
    content: string;
    streaming?: boolean;
    sources?: Array<{
        doc: string;
        page: number;
        text: string;
    }>;
    tools_used?: number;
    tool_calls?: Array<{
        tool_name: string;
        result: any;
    }>;
    memory_used?: boolean;
}

export default function CleanPDFRagPage() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    co
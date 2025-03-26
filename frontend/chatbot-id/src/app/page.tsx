"use client";

import React, { Key, useEffect, useRef, useState } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import Cookies from "js-cookie";

// UI components (modifica según tu estructura)
import {
  ChatBubble,
  ChatBubbleAction,
  ChatBubbleAvatar,
  ChatBubbleMessage,
} from "@/components/ui/chat/chat-bubble";
import { ChatInput } from "@/components/ui/chat/chat-input";
import { ChatMessageList } from "@/components/ui/chat/chat-message-list";
import { Button } from "@/components/ui/button";
import {
  CopyIcon,
  CornerDownLeft,
  Paperclip,
  RefreshCcw,
} from "lucide-react";

// Definimos tipo local de mensaje
type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  attachments?: { name: string }[];
};

const ChatAiIcons = [
  { icon: CopyIcon, label: "Copy" },
  { icon: RefreshCcw, label: "Refresh" },
];

export default function Home() {
  const [conversationId, setConversationId] = useState<string | null>(null);

  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [attachedFiles, setAttachedFiles] = useState<File[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [latexContent, setLatexContent] = useState(""); // Para .tex (opcional)

  const messagesRef = useRef<HTMLDivElement>(null);

  // Al montar, si ya hay un convId en cookies, lo usamos
  useEffect(() => {
    const existingConv = Cookies.get("conversation_id");
    if (existingConv) {
      console.log("Conversation cookie found:", existingConv);
      setConversationId(existingConv);
      fetchHistory(existingConv);
    } else {
      // Creamos un conv nuevo
      createNewConversation();
    }
  }, []);

  // Auto-scroll al final cuando cambian messages
  useEffect(() => {
    if (messagesRef.current) {
      messagesRef.current.scrollTop = messagesRef.current.scrollHeight;
    }
    // Podrías cargar .tex (usando conv_id) si lo deseas.
  }, [messages]);

  // Crea un nuevo conv ID
  const createNewConversation = async () => {
    try {
      const resp = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/start`, {
        method: "GET",
      });
      if (!resp.ok) {
        throw new Error(`Error creating conversation: ${resp.statusText}`);
      }
      const data = await resp.json();
      const newConvId = data.conversation_id;
      Cookies.set("conversation_id", newConvId, { expires: 1 / 24 });
      setConversationId(newConvId);
      console.log("New conversation_id:", newConvId);
    } catch (error) {
      console.error("Failed to create conversation:", error);
    }
  };

  // Fetch local history from /history if you store it
  const fetchHistory = async (convId: string) => {
    // Optional: if your backend has an endpoint "/history?conversation_id=..."
    try {
      const resp = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/history?conversation_id=${convId}`
      );
      if (resp.ok) {
        const data = await resp.json();
        // data.data = array of messages
        if (data.data) setMessages(data.data);
      }
    } catch (error) {
      console.error("Error fetching conversation history:", error);
    }
  };

  // Subir archivos al pipeline
  const handleFileUpload = async () => {
    if (!conversationId || attachedFiles.length === 0) return;

    const formData = new FormData();
    formData.append("conversation_id", conversationId);
    attachedFiles.forEach((f) => formData.append("files", f));

    try {
      const resp = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/upload`,
        {
          method: "POST",
          body: formData,
        }
      );
      if (!resp.ok) {
        throw new Error(`File upload failed: ${resp.statusText}`);
      }
      const data = await resp.json();
      console.log("Files uploaded:", data.message);
    } catch (err) {
      console.error("Error uploading files:", err);
    } finally {
      // Limpia la lista de adjuntos
      setAttachedFiles([]);
    }
  };

  // Al mandar texto -> /chat pipeline
  const handleSendMessage = async () => {
    if (!conversationId || !input.trim()) return;
    setIsLoading(true);

    // Añadimos el mensaje "user" al local
    const newUserMsg: ChatMessage = { role: "user", content: input };
    if (attachedFiles.length > 0) {
      newUserMsg.attachments = attachedFiles.map((f) => ({ name: f.name }));
    }

    setMessages((prev) => [...prev, newUserMsg]);

    try {
      // Primero subimos archivos (si hay)
      if (attachedFiles.length > 0) {
        await handleFileUpload(); // sube e ingesta
      }

      // Llamamos a /chat con conversation_id y el "message"
      const formData = new FormData();
      formData.append("conversation_id", conversationId);
      formData.append("message", input);

      const resp = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/chat`,
        {
          method: "POST",
          body: formData,
        }
      );
      if (!resp.ok) {
        throw new Error(`Error: ${resp.statusText}`);
      }
      const data = await resp.json();

      // Añadimos la respuesta "assistant"
      const newAssistMsg: ChatMessage = {
        role: "assistant",
        content: data.response || "",
      };
      setMessages((prev) => [...prev, newAssistMsg]);
    } catch (error) {
      console.error("Failed to send message:", error);
    } finally {
      setInput("");
      setIsLoading(false);
      setIsGenerating(false);
    }
  };

  // Manejador de submit
  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!input.trim()) return;
    setIsGenerating(true);
    handleSendMessage();
  };

  // Manejador de input-file
  const handleFileAttach = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files) {
      setAttachedFiles((prev) => [...prev, ...Array.from(files)]);
    }
  };

  // Acciones (copy, refresh)
  const handleActionClick = (action: string, index: number) => {
    if (action === "Copy") {
      navigator.clipboard.writeText(messages[index].content);
    }
    else if (action === "Refresh") {
      console.log("Refresh clicked");
    }
  };

  return (
    <>
      <header className="h-[10vh] w-full flex items-center justify-between bg-background px-6 py-4 shadow-md">
        <div className="flex items-center gap-2">
          <img src="/logo_icono.jpg" alt="Logo" className="h-8 object-contain" />
        </div>
        <Button variant="ghost" size="default" className="gap-1.5">
          Mi Cuenta
        </Button>
      </header>

      <main className="h-[75vh] w-full flex items-center justify-center mx-auto py-6">
        <div className={`${latexContent ? "w-3/5" : "w-full max-w-6xl"} h-full px-4`}>
          <ChatMessageList ref={messagesRef}>
            {messages.length === 0 && (
              <div className="w-full bg-background shadow-sm border rounded-lg p-8 flex flex-col gap-2">
                <h1 className="font-bold">IA Disclosure</h1>
                <p className="text-muted-foreground text-sm">
                  Use esta interfaz para subir documentos e interactuar con la IA.
                </p>
              </div>
            )}

            {messages.map((msg, i) => (
              <ChatBubble
                key={i}
                variant={msg.role === "user" ? "sent" : "received"}
              >
                <ChatBubbleAvatar
                  src=""
                  fallback={msg.role === "user" ? "👨🏽" : "🤖"}
                />
                <ChatBubbleMessage>
                  <Markdown remarkPlugins={[remarkGfm]}>{msg.content}</Markdown>
                  {msg.attachments && msg.attachments.length > 0 && (
                    <div className="flex items-center mt-1.5 gap-2">
                      <Paperclip className="size-4" />
                      <ul className="text-sm">
                        {msg.attachments.map((att, idx) => (
                          <li key={idx}>{att.name}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {msg.role === "assistant" &&
                    i === messages.length - 1 &&
                    !isGenerating && (
                      <div className="flex items-center mt-1.5 gap-1">
                        {ChatAiIcons.map((icon, idx2) => {
                          const Icon = icon.icon;
                          return (
                            <ChatBubbleAction
                              variant="outline"
                              className="size-6"
                              key={idx2}
                              icon={<Icon className="size-3" />}
                              onClick={() => handleActionClick(icon.label, i)}
                            />
                          );
                        })}
                      </div>
                    )}
                </ChatBubbleMessage>
              </ChatBubble>
            ))}

            {isGenerating && (
              <ChatBubble variant="received">
                <ChatBubbleAvatar src="" fallback="🤖" />
                <ChatBubbleMessage isLoading />
              </ChatBubble>
            )}
          </ChatMessageList>

          <div className="w-full px-2">
            <form
              onSubmit={handleSubmit}
              className="relative rounded-lg border bg-background focus-within:ring-1 focus-within:ring-ring"
            >
              {attachedFiles.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-2">
                  {attachedFiles.map((file, idx) => (
                    <div
                      key={idx}
                      className="flex items-center gap-2 p-2 bg-muted rounded-md border"
                    >
                      <Paperclip className="size-4" />
                      <span className="text-sm truncate max-w-[200px]">
                        {file.name}
                      </span>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() =>
                          setAttachedFiles((prev) =>
                            prev.filter((_, fIndex) => fIndex !== idx)
                          )
                        }
                      >
                        <span className="sr-only">Remove file</span>
                        ✖
                      </Button>
                    </div>
                  ))}
                </div>
              )}

              <ChatInput
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Escriba su mensaje..."
              />
              <div className="flex items-center p-3 pt-0">
                <input
                  id="file-input"
                  type="file"
                  multiple
                  style={{ display: "none" }}
                  onChange={(e) => {
                    handleFileAttach(e);
                    // e.target.value = ""; // si quieres permitir volver a subir el mismo archivo
                  }}
                />
                <Button
                  variant="ghost"
                  size="icon"
                  type="button"
                  onClick={() => document.getElementById("file-input")?.click()}
                >
                  <Paperclip className="size-4" />
                  <span className="sr-only">Attach file</span>
                </Button>

                <Button
                  disabled={!input || isLoading}
                  type="submit"
                  size="sm"
                  className="ml-auto gap-1.5"
                >
                  Enviar
                  <CornerDownLeft className="size-3.5" />
                </Button>
              </div>
            </form>
          </div>
        </div>

        {latexContent && (
          <div className="w-2/5 px-2 h-full overflow-auto">
            <h2 className="text-lg font-bold mb-4">Vista Previa LaTeX</h2>
            <div className="border p-4 rounded-lg bg-gray-100">
              <pre className="text-sm overflow-auto">
                {latexContent || "La vista previa de LaTeX aparecerá aquí..."}
              </pre>
            </div>
          </div>
        )}
      </main>
    </>
  );
}

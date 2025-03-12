"use client";

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
  Mic,
  Paperclip,
  RefreshCcw,
  //Send,
  Volume2,
} from "lucide-react";
import React, { Key, useEffect, useRef, useState} from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import Cookies from "js-cookie";

const ChatAiIcons = [
  {
    icon: CopyIcon,
    label: "Copy",
  },
  {
    icon: RefreshCcw,
    label: "Refresh",
  }
];

export default function Home() {
  const [input, setInput] = React.useState<string>("");
  const [messages, setMessages] = useState<{ role: string; content: string }[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [attachedFiles, setAttachedFiles] = useState<File[]>([]);
  const [latexContent, setLatexContent] = useState<string>(""); // Para manejar el contenido LaTeX

  const messagesRef = useRef<HTMLDivElement>(null);
  const formRef = useRef<HTMLFormElement>(null);

  useEffect(() => {
    const handleExistingThread = async () => {
      const threadId = Cookies.get("thread_id");
      if (threadId) {
        console.log(`Cookie ya existe ${threadId}`);
        await fetchThreadHistory();
        await fetchDocument();
      }
    };
  
    handleExistingThread();
  }, []);

  useEffect(() => {
    if (messagesRef.current) {
        messagesRef.current.scrollTop = messagesRef.current.scrollHeight;
      }
    fetchDocument();
    }, [messages]);

  const fetchDocument = async () =>{
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/readTextFile?thread_id=${Cookies.get("thread_id")}`);
    if (!response.ok) {
      throw new Error(`Error fetching history: ${response.statusText}`);
    }
    const data = await response.json();
    setLatexContent(data['response'])
  }  

  const fetchThreadHistory = async () => {
      try {
        const threadId = Cookies.get("thread_id");
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/threadHistory?thread_id=${threadId}`);
        if (!response.ok) {
          throw new Error(`Error fetching history: ${response.statusText}`);
        }
  
        const data = await response.json();
  
        setMessages(
          data.data.map((message: { role: any; content: { text: { value: any; }; }[]; }) => ({
            role: message.role,
            content: message.content[0]?.text?.value || "",
          }))
        );
      } catch (error) {
        console.error("Error fetching thread history:", error);
      }
    };

  const fetchNewThread = async () =>{
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/start`);
      if (!response.ok) {
        throw new Error(`Error fetching history: ${response.statusText}`);
      }
      const data = await response.json();
      return data['thread_id'];
    } catch (error) {
      console.error("Error fetching thread history:", error);
      return null;
    }
  }  
  
  // Simulated handlers
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
  };


  // Función para enviar el mensaje y actualizar el historial
  const handleSendMessage = async (userInput: string) => {
    const threadId = Cookies.get("thread_id");
    console.log(JSON.stringify({ message: userInput, thread_id: threadId }));
    setIsLoading(true);
    setMessages((prevMessages) => [
      ...prevMessages,
      { role: "user", content: userInput }
    ]);
    try {
      const threadId = Cookies.get("thread_id");
      if(!threadId) {
        const newThreadId = await fetchNewThread();
        if (newThreadId) {
          Cookies.set("thread_id", newThreadId, { expires: 1 / 24 }); // 1 hora
          console.log("Cookie creada");
        } else {
          console.log("Error al generar el thread");
        }
      }

      const formData = new FormData();
      formData.append("message", userInput);
      formData.append("thread_id", Cookies.get("thread_id") || "");
  
      // Adjuntar archivos al FormData
      attachedFiles.forEach((file) => {
        formData.append("files", file);
      });

      setAttachedFiles([]);

      // Realizar la solicitud a la API /sendMessage
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/chat`,
        {
          method: "POST",
          body: formData
        }
      );

      if (!response.ok) {
        throw new Error(`Error sending message: ${response.statusText}`);
      }
    
      const responseData = await response.json();
      console.log('Response data:', responseData);

      setMessages((prevMessages) => [
        ...prevMessages,
        { role: "assistant", content: responseData.response }
      ]);

    } catch (error) {
      console.error("Error sending message:", error);
    } finally {
      setIsLoading(false);
      setIsGenerating(false);
    }
  };

  // Manejador de formulario para enviar el mensaje
  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setInput("");
    if (!input.trim()) return;
    await handleSendMessage(input);

  };

  const handleFileAttach = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files) {
      setAttachedFiles((prev) => [...prev, ...Array.from(files)]);
    }
  };

  const reload = async () => {
    setIsLoading(true);
    setTimeout(() => {
      setIsLoading(false);
    }, 1000); // Simulated reload
  };

  const onSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsGenerating(true);
    if (messagesRef.current) {
      messagesRef.current.scrollTop = messagesRef.current.scrollHeight;
    }
    handleSubmit(e);
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      if (isGenerating || isLoading || !input) return;
      onSubmit(e as unknown as React.FormEvent<HTMLFormElement>);
    }
  };

  const handleActionClick = async (action: string, messageIndex: number) => {
    console.log("Action clicked:", action, "Message index:", messageIndex);
    if (action === "Refresh") {
      setIsGenerating(true);
      try {
        await reload();
      } catch (error) {
        console.error("Error reloading:", error);
      } finally {
        setIsGenerating(false);
      }
    }

    if (action === "Copy") {
      const message = messages[messageIndex];
      if (message && message.role === "assistant") {
        navigator.clipboard.writeText(message.content);
      }
    }
  };


  return (
    <>
      <header className="h-[10vh] w-full flex items-center justify-between bg-background px-6 py-4 shadow-md">
      {/* Logo */}
      <div className="flex items-center gap-2">
        <img
          src="/logo_icono.jpg"
          alt="Logo"
          className="h-8 object-contain"
        />
      </div>
      {/* Mi Cuenta Button */}
      <Button variant="ghost" size="default" className="gap-1.5">
        Mi Cuenta
      </Button>
    </header>
      <main className="h-[75vh] w-full flex items-center justify-center mx-auto py-6">
       <div className={`${latexContent === "" ? "w-full max-w-6xl h-full" : "w-3/5 h-full px-4"}`}>
       <ChatMessageList ref={messagesRef}>
          {/* Initial Message */}
          {messages.length === 0 && (
              <div className="w-full bg-background shadow-sm border rounded-lg p-8 flex flex-col gap-2">
                <h1 className="font-bold">IA para invention disclousure</h1>
                <p className="text-muted-foreground text-sm">
                Esta aplicación web está diseñada para ayudar a generar divulgaciones de invención completas de manera eficiente. Impulsada por la integración de IA, simplifica el proceso de detallar los aspectos técnicos e innovadores de su invención.
                </p>
                <p className="text-muted-foreground text-sm">
                ¡Explore las funciones de soporte intuitivas disponibles y haga que su proceso de divulgación de invención sea más sencillo que nunca!
                </p>
              </div>
          )}

          {/* Messages */}
          {messages &&
              messages.map((message: { role: string; content: string; }, index: Key | null | undefined) => (
            <ChatBubble
              key={index}
              variant={message.role == "user" ? "sent" : "received"}
            >
              <ChatBubbleAvatar
                src=""
                fallback={message.role == "user" ? "👨🏽" : "🤖"}
              />
              <ChatBubbleMessage>
                <Markdown key="markdown-content" remarkPlugins={[remarkGfm]}>
                  {message.content}
                </Markdown>

                {message.role === "assistant" &&
                  messages.length - 1 === index && (
                    <div className="flex items-center mt-1.5 gap-1">
                      {!isGenerating && (
                        <>
                          {ChatAiIcons.map((icon, iconIndex) => {
                            const Icon = icon.icon;
                            return (
                              <ChatBubbleAction
                                variant="outline"
                                className="size-6"
                                key={iconIndex}
                                icon={<Icon className="size-3" />}
                                onClick={() =>
                                  handleActionClick(icon.label, index)
                                }
                              />
                            );
                          })}
                        </>
                      )}
                    </div>
                  )}
              </ChatBubbleMessage>
            </ChatBubble>
          ))}

        {/* Loading */}
        {isGenerating && (
          <ChatBubble variant="received">
            <ChatBubbleAvatar src="" fallback="🤖" />
            <ChatBubbleMessage isLoading />
          </ChatBubble>
        )}
      </ChatMessageList>
      <div className="w-full px-2">
        <form
          ref={formRef}
          onSubmit={onSubmit}
          className="relative rounded-lg border bg-background focus-within:ring-1 focus-within:ring-ring"
        >
          {attachedFiles.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-2">
            {attachedFiles.map((file, index) => (
              <div
                key={index}
                className="flex items-center gap-2 p-2 bg-muted rounded-md border"
              >
                <Paperclip className="size-4" />
                <span className="text-sm truncate max-w-[200px]">{file.name}</span>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() =>
                    setAttachedFiles((prev) =>
                      prev.filter((_, i) => i !== index)
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
            onKeyDown={onKeyDown}
            onChange={handleInputChange}
            placeholder="Escriba su mensaje aquí..."
            className="min-h-12 resize-none rounded-lg bg-background border-0 p-3 shadow-none focus-visible:ring-0"
          />
          <div className="flex items-center p-3 pt-0">
            <input
              id="file-input"
              type="file"
              multiple
              style={{ display: "none" }}
              onChange={(e) => {
                handleFileAttach(e);
                e.target.value = ""; // Resetea el valor del input para permitir volver a subir el mismo archivo
              }}
            />
            <Button variant="ghost" size="icon" type="button" onClick={() => document.getElementById("file-input")?.click()}>
              <Paperclip className="size-4" />
              <span className="sr-only">Attach file</span>
            </Button>

            <Button
              disabled={!input || isLoading}
              type="submit"
              size="sm"
              className="ml-auto gap-1.5"
            >
              Enviar mensaje
              <CornerDownLeft className="size-3.5" />
            </Button>
          </div>
        </form>
      </div>
    </div>
    {latexContent != "" && (
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

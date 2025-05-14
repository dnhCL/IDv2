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
  Volume2,
} from "lucide-react";
import React, { Key, useEffect, useRef, useState } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import Cookies from "js-cookie";

// *** NEW: Extend your message type to allow attachments
type ChatMessage = {
  role: string;
  content: string;
  attachments?: { name: string }[]; // we store array of {name}
};

const ChatAiIcons = [
  {
    icon: CopyIcon,
    label: "Copy",
  },
  {
    icon: RefreshCcw,
    label: "Refresh",
  },
];

export default function Home() {
  const [input, setInput] = useState<string>("");
  // *** NEW: We now use ChatMessage type
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [attachedFiles, setAttachedFiles] = useState<File[]>([]);
  const [latexContent, setLatexContent] = useState<string>(""); // Para manejar el contenido LaTeX

  // Estado para verificar si el PDF existe
  const [pdfExists, setPdfExists] = useState(false);


  const messagesRef = useRef<HTMLDivElement>(null);
  const formRef = useRef<HTMLFormElement>(null);

  useEffect(() => {
    const handleExistingThread = async () => {
      const threadId = Cookies.get("thread_id");
      const response = await validateAssistantId()
      if (threadId && response) {
        console.log(`Cookie ya existe ${threadId}`);
        await fetchThreadHistory();
        await fetchDocument();
        checkPdfExistence(threadId); // Verificar si el PDF existe cuando ya hay un hilo
      } else {
        handleSendMessage("Hola!");
      }
    };

    handleExistingThread();
  }, []);

  useEffect(() => {
    if (messagesRef.current) {
      messagesRef.current.scrollTop = messagesRef.current.scrollHeight;
    }
    const handleFetchDocument = async () => {
      try {
        const threadId = Cookies.get("thread_id");
        const response = await validateAssistantId();
        if (threadId && response) {
          await fetchDocument();
        }
      } catch (error) {
        console.error("Error al obtener el documento:", error);
      }
    }

    handleFetchDocument()

    const threadId = Cookies.get("thread_id");
    if (threadId) {
      checkPdfExistence(threadId); // Verificar si el PDF existe cuando ya hay un hilo
    }

  }, [messages]);

  useEffect(()=>{
    console.log("attachedFiles final", attachedFiles);
  },[attachedFiles])

  // Verificar si el PDF existe en el backend
  const checkPdfExistence = async (threadId: string) => {
    try {
      const response = await fetch(`/pdf/${threadId}/${threadId}.pdf`, { method: "HEAD" });
      if (response.ok) {
        setPdfExists(true); // El archivo PDF existe
      } else {
        setPdfExists(false); // El archivo PDF no existe
      }
    } catch (error) {
      console.error("Error checking PDF existence:", error);
      setPdfExists(false); // Si hay un error, asumimos que el archivo no existe
    }
  };

  const validateAssistantId = async () => {
    try {
      // Aquí se hace la solicitud a la API de OpenAI para validar el thread_id
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/listAssistants`);
      const assistId = Cookies.get("assistant_id");
      console.log(assistId);


      if (response.ok && !!assistId && assistId !== "") {
        const data = await response.json();
        console.log("data", data);
        const valido = data.includes(assistId);
        console.log(valido);

        if (valido) {
          // Si el thread_id es válido
          return true;
        } else {
          // Si el thread_id no es válido
          Cookies.remove("assistant_id");
          Cookies.remove("thread_id");
          Cookies.remove("vectore_store_id");
          return false;
        }
      } else {
        // console.error("Error en la validación del thread_id:", response.statusText);
        return false;
      }
    } catch (error) {
      console.error("Error al validar el thread_id:", error);
      return false;
    }
  };

  const fetchDocument = async () => {
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/readTextFile?thread_id=${Cookies.get(
        "thread_id"
      )}`
    );
    if (!response.ok) {
      throw new Error(`Error fetching history: ${response.statusText}`);
    }
    const data = await response.json();
    setLatexContent(data["response"]);
  };

  const fetchThreadHistory = async () => {
    try {
      const threadId = Cookies.get("thread_id");
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/threadHistory?thread_id=${threadId}`
      );
      if (!response.ok) {
        throw new Error(`Error fetching history: ${response.statusText}`);
      }

      const data = await response.json();

      setMessages(
        data.data.map(
          (message: { role: any; content: { text: { value: any } }[] }) => ({
            role: message.role,
            content: message.content[0]?.text?.value || "",
          })
        )
      );
    } catch (error) {
      console.error("Error fetching thread history:", error);
    }
  };

  const fetchNewThread = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/start`);
      if (!response.ok) {
        throw new Error(`Error fetching thread: ${response.statusText}`);
      }
      const data = await response.json();

      // data tiene: { thread_id, assistant_id, vector_store_id }
      // Guardarlos en cookies
      let expirationDays = parseInt(`${process.env.COOKIES_DURATION}`) / 1440;

      Cookies.set("thread_id", data.thread_id, { expires: expirationDays });
      Cookies.set("assistant_id", data.assistant_id, { expires: expirationDays });
      Cookies.set("vector_store_id", data.vector_store_id, { expires: expirationDays });

      return {
        thread_id: data.thread_id,
        assistant_id: data.assistant_id,
        vector_store_id: data.vector_store_id,
      };
    } catch (error) {
      console.error("Error fetching thread:", error);
      return null;
    }
  };

  // Simulated handlers
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
  };

  // *** NEW: Al mandar mensaje, añade attachments en el mensaje "user"
  //  y limpia attachedFiles al final (después de la respuesta).
  // const handleSendMessage = async (userInput: string) => {
  //   setIsLoading(true);

  //   // 1) Añadimos un "mensaje de usuario" al estado con attachments
  //   setMessages((prev) => [
  //     ...prev,
  //     {
  //       role: "user",
  //       content: userInput,
  //       attachments: attachedFiles.map((f) => ({ name: f.name })), // *** store names
  //     },
  //   ]);

  //   try {
  //     let threadId = Cookies.get("thread_id");
  //     let assistantId = Cookies.get("assistant_id");
  //     let vectorStoreId = Cookies.get("vector_store_id");

  //     if (!threadId || !assistantId || !vectorStoreId) {
  //       const newData = await fetchNewThread();
  //       if (newData) {
  //         threadId = newData.thread_id;
  //         assistantId = newData.assistant_id;
  //         vectorStoreId = newData.vector_store_id;
  //         console.log("Cookies creadas para nueva conversación efímera");
  //       } else {
  //         console.log("Error al generar el thread");
  //         return;
  //       }
  //     }

  //     // 2) Creamos FormData con message y los archivos
  //     const formData = new FormData();
  //     formData.append("message", userInput);
  //     formData.append("thread_id", threadId ?? "");
  //     formData.append("assistant_id", assistantId ?? "");
  //     formData.append("vector_store_id", vectorStoreId ?? "");

  //     attachedFiles.forEach((file) => {
  //       formData.append("files", file);
  //     });

  //     // *** NO limpiamos "attachedFiles" aquí todavía

  //     const response = await fetch(
  //       `${process.env.NEXT_PUBLIC_API_URL}/chat`,
  //       {
  //         method: "POST",
  //         body: formData,
  //       }
  //     );

  //     if (!response.ok) {
  //       throw new Error(`Error sending message: ${response.statusText}`);
  //     }

  //     const responseData = await response.json();

  //     // 3) Añadimos la respuesta del asistente al estado
  //     setMessages((prev) => [
  //       ...prev,
  //       { role: "assistant", content: responseData.response },
  //     ]);
  //   } catch (error) {
  //     console.error("Error sending message:", error);
  //   } finally {
  //     setIsLoading(false);
  //     setIsGenerating(false);
  //     // *** NEW: Limpiamos la lista de archivos para el próximo envío
  //     setAttachedFiles([]);
  //   }
  // };

  const handleSendMessage = async (userInput: string) => {
    setIsLoading(true);

    // 1) Añadimos un "mensaje de usuario" al estado con attachments
    setMessages((prev) => [
      ...prev,
      {
        role: "user",
        content: userInput,
        attachments: attachedFiles.map((f) => ({ name: f.name })), // *** store names
      },
    ]);

    try {
      let threadId = Cookies.get("thread_id");
      let assistantId = Cookies.get("assistant_id");
      let vectorStoreId = Cookies.get("vector_store_id");

      if (!threadId || !assistantId || !vectorStoreId) {
        const newData = await fetchNewThread();
        if (newData) {
          threadId = newData.thread_id;
          assistantId = newData.assistant_id;
          vectorStoreId = newData.vector_store_id;
          console.log("Cookies creadas para nueva conversación efímera");
        } else {
          console.log("Error al generar el thread");
          return;
        }
      }

      // 2) Creamos FormData con message y los archivos
      const formData = new FormData();
      formData.append("message", userInput);
      formData.append("thread_id", threadId ?? "");
      formData.append("assistant_id", assistantId ?? "");
      formData.append("vector_store_id", vectorStoreId ?? "");

      // Solo enviamos los archivos adjuntos actuales
      attachedFiles.forEach((file) => {
        formData.append("files", file);
      });

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/chat`,
        {
          method: "POST",
          body: formData,
        }
      );

      if (!response.ok) {
        throw new Error(`Error sending message: ${response.statusText}`);
      }

      const responseData = await response.json();

      // 3) Añadimos la respuesta del asistente al estado
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: responseData.response },
      ]);
    } catch (error) {
      console.error("Error sending message:", error);
    } finally {
      setIsLoading(false);
      setIsGenerating(false);
      // Limpiamos los archivos después de haber enviado el mensaje
      setAttachedFiles([]);
    }
  };

  // Manejador de formulario para enviar el mensaje
  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setInput("");
    if (!input.trim()) return;
    await handleSendMessage(input);
  };

  // *** La parte de adjuntar archivos
  const handleFileAttach = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    console.log("files en handlefileattach", files)
    if (files && files?.length > 0) {
      console.log("setear attached files", attachedFiles, Array.from(files));
      const newFiles = [...attachedFiles, ...Array.from(files)];
      // Definiendo previamente el nuevo estado attachedFiles, se evitan los errores de adjuntar archivos
      setAttachedFiles(newFiles);
      console.log("attachedFiles", attachedFiles.length);
    }else{
      console.log("no hay archivos seleccionados");
    }

    // e.target.value = ""; // si quieres permitir subir el mismo archivo repetido
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
          <img src="/logo_icono.jpg" alt="Logo" className="h-8 object-contain" />
        </div>
        {/* Mi Cuenta Button */}
        <Button variant="ghost" size="default" className="gap-1.5">
          Mi Cuenta
        </Button>
      </header>

      <main className="h-[75vh] w-full flex items-center justify-center mx-auto py-6">
        <div
          className={`${(latexContent === "" && pdfExists) ? "w-full max-w-6xl h-full" : "w-3/5 h-full px-4"
            }`}
        >
          <ChatMessageList ref={messagesRef}>
            {/* Initial Message */}
            {messages.length === 0 && (
              <div className="w-full bg-background shadow-sm border rounded-lg p-8 flex flex-col gap-2">
                <h1 className="font-bold">IA para invention disclosure</h1>
                <p className="text-muted-foreground text-sm">
                  Esta aplicación web está diseñada para ayudar a generar divulgaciones de
                  invención completas de manera eficiente. Impulsada por la integración de
                  IA, simplifica el proceso de detallar los aspectos técnicos e innovadores
                  de su invención.
                </p>
                <p className="text-muted-foreground text-sm">
                  ¡Explore las funciones de soporte intuitivas disponibles y haga que su
                  proceso de divulgación de invención sea más sencillo que nunca!
                </p>
              </div>
            )}

            {/* Messages */}
            {messages.map((message, index) => (
              <ChatBubble
                key={index}
                variant={message.role === "user" ? "sent" : "received"}
              >
                <ChatBubbleAvatar
                  src=""
                  fallback={message.role === "user" ? "👨🏽" : "🤖"}
                />
                <ChatBubbleMessage>
                  <Markdown remarkPlugins={[remarkGfm]}>{message.content}</Markdown>

                  {/* *** NEW: Si el mensaje tiene attachments, mostramos un clip + lista */}
                  {message.attachments && message.attachments.length > 0 && (
                    <div className="flex items-center mt-1.5 gap-2">
                      <Paperclip className="size-4" />
                      <ul className="text-sm">
                        {message.attachments.map((att, attIndex) => (
                          <li key={attIndex}>{att.name}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Botones en la burbuja si es el último mensaje del assistant */}
                  {message.role === "assistant" &&
                    index === messages.length - 1 &&
                    !isGenerating && (
                      <div className="flex items-center mt-1.5 gap-1">
                        {ChatAiIcons.map((icon, iconIndex) => {
                          const Icon = icon.icon;
                          return (
                            <ChatBubbleAction
                              variant="outline"
                              className="size-6"
                              key={iconIndex}
                              icon={<Icon className="size-3" />}
                              onClick={() => handleActionClick(icon.label, index)}
                            />
                          );
                        })}
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
              {(attachedFiles.length > 0 && !isLoading) && (
                <div className="flex flex-wrap gap-2 mb-2">
                  {attachedFiles.map((file, index) => (
                    <div
                      key={index}
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
                    e.target.value = ""; // Resetea el valor del input (opcional)
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
                  Enviar mensaje
                  <CornerDownLeft className="size-3.5" />
                </Button>
              </div>
            </form>
          </div>
        </div>

        {latexContent !== "" && pdfExists && (
          <div className="w-2/5 px-2 h-full overflow-auto">
            <h2 className="text-lg font-bold mb-4">Vista Previa PDF</h2>
            <iframe
              src={`/pdf/${Cookies.get("thread_id")}/${Cookies.get("thread_id")}.pdf?refresh=${new Date().getTime()}`}
              className="w-full h-[90vh] border"
              title="PDF Preview"
            />

          </div>
        )}

      </main>
    </>
  );
}
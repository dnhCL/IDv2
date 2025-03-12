import { useEffect, useState } from "react";

// Define los tipos de la respuesta esperada
export interface MessageContent {
  text: {
    annotations: any[];
    value: string;
  };
  type: string;
}

export interface Message {
  assistant_id: string | null;
  attachments: any[];
  content: MessageContent[];
  created_at: number;
  id: string;
  metadata: object;
  object: string;
  role: "assistant" | "user";
  run_id: string | null;
  thread_id: string;
}

export interface FetchResponse {
  data: Message[];
  first_id: string;
  has_more: boolean;
  last_id: string;
  object: string;
}

export interface UseFetchReturn<T> {
  data: T | null;
  isLoading: boolean;
  hasError: Error | null;
  setUrl: React.Dispatch<React.SetStateAction<string>>;
}

export const useFetch = <T = any>(apiUrl: string): UseFetchReturn<T> => {
  const [url, setUrl] = useState(apiUrl);
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState<Error | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);

      try {
        const response = await fetch(url, {
          headers: {
            accept: "application/json",
            "User-agent": "learning app",
          },
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const responseData = await response.json();
        setData(responseData);
        setIsLoading(false);
        setHasError(null);
      } catch (error: any) {
        setIsLoading(false);
        setHasError(error);
      }
    };

    fetchData();
  }, [url]);

  return { data, isLoading, hasError, setUrl };
};

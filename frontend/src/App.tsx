import { useState, useRef, useEffect } from "react";
import { ChevronDown, Sparkles } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ChatMessage } from "@/components/ChatMessage";
import { TypingIndicator } from "@/components/TypingIndicator";
import { ChatInput } from "@/components/ChatInput";
import { ChatHeader } from "@/components/ChatHeader";
import { GengarIcon } from "@/components/GengarIcon";
import { ErrorAlert } from "@/components/ErrorAlert";
import { chatApi } from "@/services/api";
import type { Message } from "@/types/chat";

const EXAMPLE_QUESTIONS = [
  "What is Gyarados weak to?",
  "How do I evolve Eevee into Umbreon?",
  "Can Gengar learn Thunderbolt?",
  "How do EVs work?",
];

function App() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "Hello! I'm EY-AY, your Pokémon assistant. What would you like to know?",
      timestamp: new Date().toISOString(),
    },
  ]);
  const [isOpen, setIsOpen] = useState(false);
  const [unread, setUnread] = useState(0);
  const [isTyping, setIsTyping] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isOnline, setIsOnline] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);
  // Replies can arrive after the user collapsed the chat; the ref sees the latest value
  const isOpenRef = useRef(isOpen);

  useEffect(() => {
    checkHealth();
  }, []);

  useEffect(() => {
    isOpenRef.current = isOpen;
    if (isOpen) setUnread(0);
  }, [isOpen]);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping, isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setIsOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [isOpen]);

  const checkHealth = async () => {
    try {
      await chatApi.checkHealth();
      setIsOnline(true);
    } catch {
      setIsOnline(false);
      setError("Backend server is offline. Please start the FastAPI server.");
    }
  };

  const addBotMessage = (message: Message) => {
    setMessages((prev) => [...prev, message]);
    if (!isOpenRef.current) setUnread((n) => n + 1);
  };

  const handleSend = async (message: string) => {
    if (isTyping) return;
    const userMessage: Message = {
      role: "user",
      content: message,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsTyping(true);
    setError(null);

    try {
      const response = await chatApi.sendMessage({
        message: message,
        session_id: sessionId,
      });

      setSessionId(response.session_id);
      addBotMessage({
        role: "assistant",
        content: response.message,
        timestamp: response.timestamp,
        intent: response.intent,
        confidence: response.confidence,
      });
      setIsOnline(true);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "An error occurred";
      console.error("Error:", err);
      setError(errorMessage);
      setIsOnline(false);

      addBotMessage({
        role: "assistant",
        content:
          "Sorry, I encountered an error. Please make sure the backend server is running.",
        timestamp: new Date().toISOString(),
        intent: "error",
        confidence: 0,
      });
    } finally {
      setIsTyping(false);
    }
  };

  const askExample = (question: string) => {
    setIsOpen(true);
    handleSend(question);
  };

  const showSuggestions = messages.length === 1 && !isTyping;

  return (
    <div className="min-h-screen bg-gengar-950 bg-[radial-gradient(ellipse_at_top_left,var(--color-gengar-700),transparent_60%),radial-gradient(ellipse_at_bottom_right,var(--color-gengar-800),transparent_55%)] text-white">
      {/* Page behind the widget */}
      <main className="mx-auto flex min-h-screen max-w-3xl flex-col justify-center px-6 py-16">
        <div className="mb-4 inline-flex w-fit items-center gap-2 rounded-full bg-gengar-700/40 px-3 py-1 text-xs text-gengar-100">
          <Sparkles className="h-3.5 w-3.5 text-gengar-eye" />
          1,025 Pokémon · moves · items · type matchups
        </div>
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
          EY-AY <span className="bg-gradient-to-r from-gengar-300 to-gengar-eye bg-clip-text text-transparent">Pokémon</span> Assistant
        </h1>
        <p className="mt-4 max-w-xl text-gengar-200/80">
          Ask about weaknesses, evolutions, learnsets, team building and game mechanics.
          Open the chat in the corner, or try one of these:
        </p>
        <div className="mt-6 flex flex-wrap gap-2">
          {EXAMPLE_QUESTIONS.map((q) => (
            <button
              key={q}
              onClick={() => askExample(q)}
              className="rounded-full border border-gengar-400/40 bg-gengar-800/40 px-4 py-2 text-sm text-gengar-50 transition hover:border-gengar-eye hover:bg-gengar-700/60"
            >
              {q}
            </button>
          ))}
        </div>
      </main>

      {/* Chat panel: full screen on phones, floating card on larger screens */}
      {isOpen && (
        <section
          role="dialog"
          aria-label="EY-AY chat"
          className="fixed inset-0 z-50 flex flex-col overflow-hidden bg-white text-gengar-950 shadow-2xl animate-in fade-in-0 slide-in-from-bottom-4 duration-200 sm:inset-auto sm:bottom-24 sm:right-6 sm:h-[min(640px,calc(100vh-8rem))] sm:w-[400px] sm:rounded-2xl sm:border sm:border-gengar-700 sm:shadow-gengar-950/60"
        >
          <header className="bg-gradient-to-r from-gengar-800 to-gengar-600 px-4 py-3.5 text-white">
            <ChatHeader isOnline={isOnline} onMinimize={() => setIsOpen(false)} />
          </header>

          <div className="min-h-0 flex-1">
            <ScrollArea className="h-full">
              <div className="px-4 py-3">
                <ErrorAlert error={error} onDismiss={() => setError(null)} />
                {messages.map((message, index) => (
                  <ChatMessage
                    key={`${message.timestamp}-${index}`}
                    message={message}
                    isUser={message.role === "user"}
                  />
                ))}
                {showSuggestions && (
                  <div className="ml-9 flex flex-wrap gap-1.5">
                    {EXAMPLE_QUESTIONS.map((q) => (
                      <button
                        key={q}
                        onClick={() => handleSend(q)}
                        className="rounded-full border border-gengar-300 px-3 py-1 text-xs text-gengar-700 transition hover:bg-gengar-600 hover:text-white"
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                )}
                {isTyping && <TypingIndicator />}
                <div ref={scrollRef} />
              </div>
            </ScrollArea>
          </div>

          <footer className="border-t border-gengar-100 p-3">
            <ChatInput onSend={handleSend} disabled={isTyping} />
          </footer>
        </section>
      )}

      {/* Launcher; hidden on phones while the full-screen chat is open */}
      <button
        onClick={() => setIsOpen((open) => !open)}
        aria-label={isOpen ? "Close chat" : "Open chat"}
        aria-expanded={isOpen}
        className={`fixed bottom-6 right-6 z-50 h-14 w-14 items-center justify-center rounded-full text-white transition hover:scale-105 ${
          isOpen
            ? "hidden bg-gengar-600 shadow-lg shadow-gengar-950/50 ring-2 ring-gengar-400/50 hover:bg-gengar-500 sm:flex"
            : "flex"
        }`}
      >
        {isOpen ? <ChevronDown className="h-6 w-6" /> : <GengarIcon className="h-14 w-14" flames />}
        {unread > 0 && !isOpen && (
          <span className="absolute -right-0.5 -top-0.5 flex h-5 min-w-5 items-center justify-center rounded-full bg-gengar-eye px-1 text-[11px] font-semibold text-white">
            {unread}
          </span>
        )}
      </button>
    </div>
  );
}

export default App;

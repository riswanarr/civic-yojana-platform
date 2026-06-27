import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { Bot, ExternalLink, Loader2, MessageSquare, Plus, Send, Sparkles, User, X } from "lucide-react";
import { apiClient } from "@/services/apiClient";
import { usePageTitle } from "@/hooks/usePageTitle";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/authStore";

type ChatbotSource = {
  scheme_id?: string;
  title?: string;
  category?: string;
  state?: string | null;
  application_link?: string | null;
};

type ChatbotResponse = {
  answer: string;
  sources: ChatbotSource[];
};

type ChatMessage = {
  id: string;
  role: "assistant" | "user";
  content: string;
  sources?: ChatbotSource[];
  followUps?: string[];
};

type ChatSession = {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messages: ChatMessage[];
};

const SUGGESTED_QUESTIONS = [
  "Which schemes can help with college scholarships?",
  "What support is available for women entrepreneurs?",
  "Find health schemes for low income families",
  "Which agriculture schemes are available in my state?"
];

const FOLLOW_UP_QUESTIONS = [
  "Scholarships for SC students in Kerala",
  "Jobs after graduation",
  "Schemes for women entrepreneurs",
  "Opportunities for minority students"
];

const CHAT_SESSIONS_STORAGE_PREFIX = "chat-sessions";
const ACTIVE_CHAT_STORAGE_PREFIX = "active-chat";
const LEGACY_CHAT_STORAGE_KEY = "gov-schemes-chat-messages";
const EMPTY_MESSAGES: ChatMessage[] = [];
const MAX_CHAT_SESSIONS = 5;

function createEmptySession(): ChatSession {
  const timestamp = new Date().toISOString();

  return {
    id: crypto.randomUUID(),
    title: "New chat",
    createdAt: timestamp,
    updatedAt: timestamp,
    messages: []
  };
}

function getSessionTitle(messages: ChatMessage[]) {
  const firstUserMessage = messages.find((message) => message.role === "user")?.content.trim();

  if (!firstUserMessage) {
    return "New chat";
  }

  return firstUserMessage.length > 48 ? `${firstUserMessage.slice(0, 45)}...` : firstUserMessage;
}

function formatSessionTimestamp(value: string) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "";
  }

  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit"
  }).format(date);
}

function normalizeSession(session: ChatSession): ChatSession {
  return {
    ...session,
    title: getSessionTitle(session.messages),
    updatedAt: session.updatedAt || session.createdAt || new Date().toISOString(),
    messages: Array.isArray(session.messages) ? session.messages : []
  };
}

function limitSessions(sessions: ChatSession[]) {
  return [...sessions]
    .sort(
      (firstSession, secondSession) =>
        new Date(secondSession.updatedAt).getTime() - new Date(firstSession.updatedAt).getTime()
    )
    .slice(0, MAX_CHAT_SESSIONS);
}

function getChatSessionsStorageKey(userId: string) {
  return `${CHAT_SESSIONS_STORAGE_PREFIX}-${userId}`;
}

function getActiveChatStorageKey(userId: string) {
  return `${ACTIVE_CHAT_STORAGE_PREFIX}-${userId}`;
}

function loadStoredSessions(userId: string | undefined): ChatSession[] {
  if (!userId) {
    return [createEmptySession()];
  }

  try {
    const storedSessions = window.localStorage.getItem(getChatSessionsStorageKey(userId));
    if (storedSessions) {
      const parsed = JSON.parse(storedSessions);
      if (Array.isArray(parsed) && parsed.length > 0) {
        return limitSessions(parsed.map((session) => normalizeSession(session)));
      }
    }

    const legacyMessages = window.localStorage.getItem(LEGACY_CHAT_STORAGE_KEY);
    if (legacyMessages) {
      const parsedMessages = JSON.parse(legacyMessages);
      if (Array.isArray(parsedMessages) && parsedMessages.length > 0) {
        const timestamp = new Date().toISOString();

        return [
          {
            id: crypto.randomUUID(),
            title: getSessionTitle(parsedMessages),
            createdAt: timestamp,
            updatedAt: timestamp,
            messages: parsedMessages
          }
        ];
      }
    }
  } catch {
    return [createEmptySession()];
  }

  return [createEmptySession()];
}

export function ChatbotPage() {
  usePageTitle("Chat Assistant | Government Schemes Discovery");

  const userId = useAuthStore((state) => state.user?.id);
  const [sessions, setSessions] = useState<ChatSession[]>(() => loadStoredSessions(userId));
  const [activeSessionId, setActiveSessionId] = useState(() =>
    userId ? window.localStorage.getItem(getActiveChatStorageKey(userId)) || "" : ""
  );
  const [question, setQuestion] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const activeSession = sessions.find((session) => session.id === activeSessionId) || sessions[0];
  const messages = activeSession?.messages ?? EMPTY_MESSAGES;
  const canSend = question.trim().length > 0 && !isLoading;

  const latestUserQuestion = useMemo(
    () => [...messages].reverse().find((message) => message.role === "user")?.content,
    [messages]
  );
  const recentSessions = useMemo(
    () =>
      [...sessions].sort(
        (firstSession, secondSession) =>
          new Date(secondSession.updatedAt).getTime() - new Date(firstSession.updatedAt).getTime()
      ),
    [sessions]
  );

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, isLoading]);

  useEffect(() => {
    const nextSessions = loadStoredSessions(userId);
    setSessions(nextSessions);
    setActiveSessionId(userId ? window.localStorage.getItem(getActiveChatStorageKey(userId)) || nextSessions[0].id : nextSessions[0].id);
    setQuestion("");
    setError(null);
  }, [userId]);

  useEffect(() => {
    if (!sessions.some((session) => session.id === activeSessionId) && sessions[0]) {
      setActiveSessionId(sessions[0].id);
    }
  }, [activeSessionId, sessions]);

  useEffect(() => {
    if (!userId) {
      return;
    }

    window.localStorage.setItem(getChatSessionsStorageKey(userId), JSON.stringify(sessions));
    window.localStorage.setItem(getActiveChatStorageKey(userId), activeSessionId);
    window.localStorage.removeItem(LEGACY_CHAT_STORAGE_KEY);
  }, [activeSessionId, sessions, userId]);

  function updateSessionMessages(sessionId: string, updater: (currentMessages: ChatMessage[]) => ChatMessage[]) {
    setSessions((currentSessions) =>
      currentSessions.map((session) => {
        if (session.id !== sessionId) {
          return session;
        }

        const nextMessages = updater(session.messages);

        return {
          ...session,
          title: getSessionTitle(nextMessages),
          updatedAt: new Date().toISOString(),
          messages: nextMessages
        };
      })
    );
  }

  async function askChatbot(nextQuestion: string) {
    const cleanedQuestion = nextQuestion.trim();
    if (!cleanedQuestion || isLoading) {
      return;
    }

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: cleanedQuestion
    };

    const targetSessionId = activeSession?.id;
    if (!targetSessionId) {
      return;
    }

    updateSessionMessages(targetSessionId, (currentMessages) => [...currentMessages, userMessage]);
    setQuestion("");
    setError(null);
    setIsLoading(true);

    try {
      const response = await apiClient.post<ChatbotResponse>("/chatbot", {
        question: cleanedQuestion
      });

      updateSessionMessages(targetSessionId, (currentMessages) => [
        ...currentMessages,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: response.answer || "I could not find a clear answer for that question.",
          sources: response.sources,
          followUps: FOLLOW_UP_QUESTIONS
        }
      ]);
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : "Unable to reach the chatbot.";
      setError(message);
      updateSessionMessages(targetSessionId, (currentMessages) => [
        ...currentMessages,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: "I could not answer that right now. Please try again in a moment.",
          followUps: FOLLOW_UP_QUESTIONS
        }
      ]);
    } finally {
      setIsLoading(false);
      window.setTimeout(() => inputRef.current?.focus(), 0);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void askChatbot(question);
  }

  function handleSuggestionClick(suggestion: string) {
    void askChatbot(suggestion);
  }

  function startNewChat() {
    const nextSession = createEmptySession();
    setSessions((currentSessions) => limitSessions([nextSession, ...currentSessions]));
    setActiveSessionId(nextSession.id);
    setQuestion("");
    setError(null);
    window.setTimeout(() => inputRef.current?.focus(), 0);
  }

  function switchSession(sessionId: string) {
    setActiveSessionId(sessionId);
    setQuestion("");
    setError(null);
    window.setTimeout(() => inputRef.current?.focus(), 0);
  }

  function deleteSession(sessionId: string) {
    const remainingSessions = limitSessions(sessions.filter((session) => session.id !== sessionId));

    if (remainingSessions.length === 0) {
      const nextSession = createEmptySession();
      setSessions([nextSession]);
      setActiveSessionId(nextSession.id);
    } else {
      setSessions(remainingSessions);

      if (sessionId === activeSession?.id) {
        setActiveSessionId(remainingSessions[0].id);
      }
    }

    setQuestion("");
    setError(null);
    window.setTimeout(() => inputRef.current?.focus(), 0);
  }

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold">Chat Assistant</h1>
          <p className="text-sm text-muted-foreground">Get concise answers from the imported government schemes.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <div className="inline-flex items-center gap-2 rounded-md border bg-background px-3 py-2 text-xs font-medium text-muted-foreground">
            <Sparkles className="h-4 w-4 text-primary" />
            {latestUserQuestion ? "Ready for follow-up" : "Scheme search ready"}
          </div>
          <button
            className="inline-flex items-center gap-2 rounded-md border bg-background px-3 py-2 text-xs font-medium text-muted-foreground hover:text-foreground"
            type="button"
            onClick={startNewChat}
          >
            <Plus className="h-4 w-4" />
            New Chat
          </button>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[280px_1fr]">
        <aside className="rounded-md border bg-background p-3">
          <div className="flex items-center justify-between gap-3 border-b pb-3">
            <div>
              <h2 className="text-sm font-semibold">Recent Chats</h2>
              <p className="mt-1 text-xs text-muted-foreground">{sessions.length} saved session{sessions.length === 1 ? "" : "s"}</p>
            </div>
            <button
              className="inline-flex h-8 w-8 items-center justify-center rounded-md border text-muted-foreground hover:text-foreground"
              type="button"
              onClick={startNewChat}
              aria-label="Start new chat"
            >
              <Plus className="h-4 w-4" />
            </button>
          </div>

          <div className="mt-3 max-h-64 space-y-2 overflow-y-auto lg:max-h-[650px]">
            {recentSessions.map((session) => (
              <div
                className={cn(
                  "flex items-start gap-2 rounded-md border p-2 transition hover:border-primary/60",
                  session.id === activeSession?.id ? "border-primary bg-primary/5" : "bg-background"
                )}
                key={session.id}
              >
                <button
                  className="flex min-w-0 flex-1 items-start gap-3 text-left"
                  type="button"
                  onClick={() => switchSession(session.id)}
                >
                  <MessageSquare className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                  <span className="min-w-0">
                    <span className="block truncate text-sm font-medium">{session.title}</span>
                    <span className="mt-1 block text-xs text-muted-foreground">{formatSessionTimestamp(session.updatedAt)}</span>
                  </span>
                </button>
                <button
                  className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground"
                  type="button"
                  onClick={() => deleteSession(session.id)}
                  aria-label={`Delete chat: ${session.title}`}
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>
        </aside>

        <section className="rounded-md border bg-background">
          <div className="flex h-[min(72vh,760px)] min-h-[560px] flex-col">
          <div className="flex-1 space-y-5 overflow-y-auto p-4 sm:p-6">
            {messages.length === 0 ? (
              <div className="flex h-full min-h-72 items-center justify-center">
                <div className="max-w-md rounded-md border bg-muted/30 p-6 text-center">
                  <div className="mx-auto flex h-11 w-11 items-center justify-center rounded-md bg-primary text-primary-foreground">
                    <Bot className="h-5 w-5" />
                  </div>
                  <p className="mt-4 text-sm leading-6 text-muted-foreground">
                    Ask about scholarships, jobs, internships, subsidies, and government opportunities.
                  </p>
                </div>
              </div>
            ) : null}

            {messages.map((message) => {
              const isUser = message.role === "user";
              const Icon = isUser ? User : Bot;

              return (
                <div className={cn("flex gap-3", isUser && "justify-end")} key={message.id}>
                  {!isUser ? (
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground">
                      <Icon className="h-4 w-4" />
                    </span>
                  ) : null}

                  <div className={cn("min-w-0 space-y-3", isUser ? "max-w-[82%] sm:max-w-[70%]" : "max-w-[88%] sm:max-w-[76%]")}>
                    <div
                      className={cn(
                        "rounded-md px-4 py-3 text-sm leading-6 shadow-sm",
                        isUser
                          ? "bg-primary text-primary-foreground"
                          : "border bg-muted/40 text-foreground"
                      )}
                    >
                      {message.content}
                    </div>

                    {!isUser && message.sources?.length ? (
                      <div className="grid gap-2 sm:grid-cols-2">
                        {message.sources.map((source, index) => (
                          <article
                            className="rounded-md border bg-background p-3 shadow-sm"
                            key={`${source.scheme_id || source.title || "source"}-${index}`}
                          >
                            <div className="flex items-start justify-between gap-3">
                              <span className="rounded-md bg-muted px-2 py-1 text-[11px] font-medium text-muted-foreground">
                                Source {index + 1}
                              </span>
                              {source.application_link ? (
                                <a
                                  className="inline-flex h-7 shrink-0 items-center gap-1 rounded-md bg-primary px-2 text-xs font-medium text-primary-foreground"
                                  href={source.application_link}
                                  rel="noreferrer"
                                  target="_blank"
                                >
                                  Apply
                                  <ExternalLink className="h-3 w-3" />
                                </a>
                              ) : null}
                            </div>

                            <h3 className="mt-3 line-clamp-2 text-sm font-semibold">
                              {source.title || "Untitled scheme"}
                            </h3>

                            <dl className="mt-3 grid gap-2 text-xs text-muted-foreground">
                              <div className="flex justify-between gap-3">
                                <dt>Category</dt>
                                <dd className="truncate text-right font-medium text-foreground">
                                  {source.category || "Not specified"}
                                </dd>
                              </div>
                              <div className="flex justify-between gap-3">
                                <dt>State</dt>
                                <dd className="truncate text-right font-medium text-foreground">
                                  {source.state || "All India"}
                                </dd>
                              </div>
                            </dl>
                          </article>
                        ))}
                      </div>
                    ) : null}

                    {!isUser && message.followUps?.length ? (
                      <div className="flex flex-wrap gap-2">
                        {message.followUps.map((followUp) => (
                          <button
                            className="rounded-md border bg-background px-3 py-2 text-left text-xs font-medium text-muted-foreground transition hover:border-primary/60 hover:text-foreground disabled:cursor-not-allowed disabled:opacity-60"
                            key={followUp}
                            type="button"
                            onClick={() => handleSuggestionClick(followUp)}
                            disabled={isLoading}
                          >
                            {followUp}
                          </button>
                        ))}
                      </div>
                    ) : null}
                  </div>

                  {isUser ? (
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
                      <Icon className="h-4 w-4" />
                    </span>
                  ) : null}
                </div>
              );
            })}

            {isLoading ? (
              <div className="flex gap-3">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground">
                  <Bot className="h-4 w-4" />
                </span>
                <div className="inline-flex items-center gap-2 rounded-md border bg-muted/40 px-4 py-3 text-sm text-muted-foreground shadow-sm">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Thinking...
                </div>
              </div>
            ) : null}
            <div ref={messagesEndRef} />
          </div>

          <div className="border-t p-4 sm:p-5">
            <div className="mb-3 flex flex-wrap gap-2">
              {SUGGESTED_QUESTIONS.map((suggestion) => (
                <button
                  className="rounded-md border bg-background px-3 py-2 text-left text-xs font-medium text-muted-foreground transition hover:border-primary/60 hover:text-foreground disabled:cursor-not-allowed disabled:opacity-60"
                  key={suggestion}
                  type="button"
                  onClick={() => handleSuggestionClick(suggestion)}
                  disabled={isLoading}
                >
                  {suggestion}
                </button>
              ))}
            </div>

            {error ? (
              <div className="mb-3 rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
                {error}
              </div>
            ) : null}

            <form className="flex flex-col gap-2 sm:flex-row" onSubmit={handleSubmit}>
              <label className="sr-only" htmlFor="chatbot-question">
                Ask a question
              </label>
              <input
                ref={inputRef}
                id="chatbot-question"
                className="h-11 min-w-0 flex-1 rounded-md border bg-background px-3 text-sm outline-none focus:border-primary"
                placeholder="Ask about eligibility, benefits, deadlines, or how to apply..."
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                disabled={isLoading}
              />
              <button
                className="inline-flex h-11 items-center justify-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground disabled:cursor-not-allowed disabled:opacity-60"
                type="submit"
                disabled={!canSend}
              >
                <Send className="h-4 w-4" />
                Send
              </button>
            </form>
          </div>
          </div>
        </section>
      </div>
    </div>
  );
}

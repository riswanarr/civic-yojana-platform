import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { BadgeCheck, Bot, ExternalLink, FileText, Loader2, MessageSquare, Plus, Send, Sparkles, User, X } from "lucide-react";
import { apiClient } from "@/services/apiClient";
import { usePageTitle } from "@/hooks/usePageTitle";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/authStore";

type ChatbotSource = {
  type?: "scheme" | "web";
  scheme_id?: string;
  title?: string;
  category?: string;
  state?: string | null;
  application_link?: string | null;
  url?: string | null;
  snippet?: string | null;
  verified?: boolean;
};

type ChatMessage = {
  id: string;
  role: "assistant" | "user";
  content: string;
  sources?: ChatbotSource[];
  followUps?: string[];
  actionLinks?: ChatActionLink[];
  usedProfile?: boolean;
  usedWebSearch?: boolean;
  createdAt?: string;
};

type ChatActionLink = {
  label: string;
  url: string;
  is_official?: boolean;
};

type ChatSession = {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messages: ChatMessage[];
  messagesLoaded?: boolean;
};

type ApiChatSession = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
};

type ApiChatMessage = {
  id: string;
  role: "assistant" | "user";
  content: string;
  sources?: ChatbotSource[];
  follow_ups?: string[];
  action_links?: ChatActionLink[];
  used_profile?: boolean;
  used_web_search?: boolean;
  created_at?: string;
};

type ChatSessionsResponse = {
  sessions: ApiChatSession[];
};

type ChatSessionResponse = {
  session: ApiChatSession;
  messages: ApiChatMessage[];
};

type CreateChatSessionResponse = {
  session: ApiChatSession;
};

type CreateChatMessageResponse = {
  session: ApiChatSession;
  user_message: ApiChatMessage;
  assistant_message: ApiChatMessage;
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

const EMPTY_MESSAGES: ChatMessage[] = [];

function getSessionTitle(messages: ChatMessage[], fallback = "New chat") {
  const firstUserMessage = messages.find((message) => message.role === "user")?.content.trim();

  if (!firstUserMessage) {
    return fallback;
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

function mapApiSession(session: ApiChatSession, existingMessages: ChatMessage[] = [], messagesLoaded = false): ChatSession {
  return {
    id: session.id,
    title: session.title || getSessionTitle(existingMessages),
    createdAt: session.created_at,
    updatedAt: session.updated_at || session.created_at,
    messages: existingMessages,
    messagesLoaded
  };
}

function mapApiMessage(message: ApiChatMessage): ChatMessage {
  return {
    id: message.id,
    role: message.role,
    content: message.content,
    sources: filterVisibleSources(message.sources || []),
    followUps: message.follow_ups || [],
    actionLinks: message.action_links || [],
    usedProfile: message.used_profile,
    usedWebSearch: message.used_web_search,
    createdAt: message.created_at
  };
}

function sourceLink(source: ChatbotSource) {
  return source.application_link || source.url || "";
}

function normalizeUrl(url?: string | null) {
  const rawUrl = (url || "").trim();
  if (!rawUrl) {
    return "";
  }

  try {
    const parsedUrl = new URL(rawUrl);
    parsedUrl.protocol = parsedUrl.protocol.toLowerCase();
    parsedUrl.hostname = parsedUrl.hostname.toLowerCase();
    parsedUrl.hash = "";
    parsedUrl.pathname = parsedUrl.pathname.replace(/\/+$/, "") || parsedUrl.pathname;

    const seenParams = new Set<string>();
    const dedupedParams = new URLSearchParams();
    parsedUrl.searchParams.forEach((value, key) => {
      const paramKey = `${key}=${value}`;
      if (seenParams.has(paramKey)) {
        return;
      }

      seenParams.add(paramKey);
      dedupedParams.append(key, value);
    });
    parsedUrl.search = dedupedParams.toString();

    return parsedUrl.toString().replace(/\/+$/, "").toLowerCase();
  } catch {
    return rawUrl.replace(/#.*$/, "").replace(/\/+$/, "").toLowerCase();
  }
}

function isInternalSource(source: ChatbotSource) {
  return source.verified === false || source.title === "Official source verification";
}

function filterVisibleSources(sources: ChatbotSource[], excludedUrls: Set<string> = new Set()) {
  const seen = new Set<string>();
  const visibleSources: ChatbotSource[] = [];

  for (const source of sources) {
    if (isInternalSource(source)) {
      continue;
    }

    const urlKey = normalizeUrl(sourceLink(source));
    if (urlKey && excludedUrls.has(urlKey)) {
      continue;
    }

    const key = source.scheme_id || urlKey || source.title;
    if (!key || seen.has(key)) {
      continue;
    }

    seen.add(key);
    visibleSources.push(source);
  }

  return visibleSources.slice(0, 2);
}

function actionLinksForMessage(message: ChatMessage) {
  const seenUrls = new Set<string>();
  const dedupeLinks = (links: ChatActionLink[]) =>
    links.filter((link) => {
      const urlKey = normalizeUrl(link.url);
      if (!urlKey || seenUrls.has(urlKey)) {
        return false;
      }

      seenUrls.add(urlKey);
      return true;
    });

  if (message.actionLinks?.length) {
    return dedupeLinks(message.actionLinks).slice(0, 3);
  }

  return dedupeLinks(
    filterVisibleSources(message.sources || [])
    .map((source): ChatActionLink | null => {
      const url = sourceLink(source);
      if (!url) {
        return null;
      }

      return {
        label: source.type === "web" ? "Open Official Portal" : "Open Official Source",
        url,
        is_official: source.type === "web" || Boolean(source.application_link)
      };
    })
    .filter((link): link is ChatActionLink => link !== null)
  ).slice(0, 3);
}

function shouldShowSourceCardsForQuestion(question?: string) {
  const normalizedQuestion = (question || "").toLowerCase();
  if (!normalizedQuestion) {
    return false;
  }

  const suppressedTerms = [
    "renew",
    "renewal",
    "deadline",
    "last date",
    "application status",
    "currently open",
    "latest notification",
    "notification",
    "documents",
    "required",
    "how do i",
    "how to",
    "eligible",
    "eligibility",
    "who is eligible"
  ];
  if (suppressedTerms.some((term) => normalizedQuestion.includes(term))) {
    return false;
  }

  return [
    "what is",
    "tell me about",
    "recommend",
    "schemes for",
    "compare",
    "government schemes"
  ].some((term) => normalizedQuestion.includes(term));
}

function visibleCardsForMessage(message: ChatMessage, question?: string) {
  if (!shouldShowSourceCardsForQuestion(question)) {
    return [];
  }

  const actionUrls = new Set(actionLinksForMessage(message).map((link) => normalizeUrl(link.url)));
  return filterVisibleSources(message.sources || [], actionUrls).slice(0, 2);
}

export function ChatbotPage() {
  usePageTitle("Chat Assistant | Government Schemes Discovery");

  const accessToken = useAuthStore((state) => state.session?.access_token);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState("");
  const [question, setQuestion] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSessionLoading, setIsSessionLoading] = useState(false);
  const [isCreatingSession, setIsCreatingSession] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const sendInFlightRef = useRef(false);
  const createSessionInFlightRef = useRef(false);

  const activeSession = sessions.find((session) => session.id === activeSessionId) || sessions[0];
  const messages = activeSession?.messages ?? EMPTY_MESSAGES;
  const canSend = Boolean(accessToken) && question.trim().length > 0 && !isLoading && !isSessionLoading;

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
    let isMounted = true;

    async function loadSessions() {
      if (!accessToken) {
        setSessions([]);
        setActiveSessionId("");
        setError("Please sign in again to use chat sessions.");
        return;
      }

      setIsSessionLoading(true);
      setError(null);

      try {
        const response = await apiClient.get<ChatSessionsResponse>("/chatbot/sessions", accessToken);
        if (!isMounted) {
          return;
        }

        const nextSessions = (response.sessions || []).map((session) => mapApiSession(session));
        setSessions(nextSessions);
        setActiveSessionId(nextSessions[0]?.id || "");
      } catch (requestError) {
        if (!isMounted) {
          return;
        }

        setSessions([]);
        setActiveSessionId("");
        setError(requestError instanceof Error ? requestError.message : "Unable to load chat sessions.");
      } finally {
        if (isMounted) {
          setIsSessionLoading(false);
        }
      }
    }

    void loadSessions();

    return () => {
      isMounted = false;
    };
  }, [accessToken]);

  useEffect(() => {
    if (!accessToken || !activeSessionId) {
      return;
    }

    const targetSession = sessions.find((session) => session.id === activeSessionId);
    if (!targetSession || targetSession.messagesLoaded) {
      return;
    }

    let isMounted = true;

    async function loadSessionMessages() {
      setIsSessionLoading(true);
      setError(null);

      try {
        const response = await apiClient.get<ChatSessionResponse>(`/chatbot/sessions/${activeSessionId}`, accessToken);
        if (!isMounted) {
          return;
        }

        setSessions((currentSessions) =>
          currentSessions.map((session) =>
            session.id === activeSessionId
              ? {
                  ...mapApiSession(response.session, response.messages.map(mapApiMessage), true)
                }
              : session
          )
        );
      } catch (requestError) {
        if (isMounted) {
          setError(requestError instanceof Error ? requestError.message : "Unable to load this chat.");
        }
      } finally {
        if (isMounted) {
          setIsSessionLoading(false);
        }
      }
    }

    void loadSessionMessages();

    return () => {
      isMounted = false;
    };
  }, [accessToken, activeSessionId, sessions]);

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
          messages: nextMessages,
          messagesLoaded: true
        };
      })
    );
  }

  async function createBackendSession(title?: string) {
    if (!accessToken) {
      throw new Error("Please sign in again to start a chat.");
    }

    const response = await apiClient.post<CreateChatSessionResponse>(
      "/chatbot/sessions",
      title ? { title } : {},
      accessToken
    );
    const nextSession = mapApiSession(response.session, [], true);
    setSessions((currentSessions) => [nextSession, ...currentSessions]);
    setActiveSessionId(nextSession.id);
    return nextSession;
  }

  async function askChatbot(nextQuestion: string) {
    const cleanedQuestion = nextQuestion.trim();
    if (!cleanedQuestion || isLoading || sendInFlightRef.current) {
      return;
    }

    if (!accessToken) {
      setError("Please sign in again to send a chat message.");
      return;
    }

    const userMessage: ChatMessage = {
      id: `pending-${crypto.randomUUID()}`,
      role: "user",
      content: cleanedQuestion,
      createdAt: new Date().toISOString()
    };

    setQuestion("");
    setError(null);
    sendInFlightRef.current = true;
    setIsLoading(true);

    try {
      const targetSession = activeSession || (await createBackendSession(cleanedQuestion));
      const targetSessionId = targetSession.id;

      updateSessionMessages(targetSessionId, (currentMessages) => [...currentMessages, userMessage]);

      const response = await apiClient.post<CreateChatMessageResponse>(
        `/chatbot/sessions/${targetSessionId}/messages`,
        {
          question: cleanedQuestion
        },
        accessToken
      );

      const assistantMessage = mapApiMessage(response.assistant_message);
      const confirmedUserMessage = mapApiMessage(response.user_message);

      updateSessionMessages(targetSessionId, (currentMessages) => [
        ...currentMessages.filter((message) => message.id !== userMessage.id),
        confirmedUserMessage,
        assistantMessage
      ]);
      setSessions((currentSessions) =>
        currentSessions.map((session) =>
          session.id === targetSessionId
            ? {
                ...session,
                title: response.session.title || getSessionTitle(session.messages, session.title),
                createdAt: response.session.created_at,
                updatedAt: response.session.updated_at
              }
            : session
        )
      );
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : "Unable to reach the chatbot.";
      setError(message);
      if (activeSession?.id) {
        updateSessionMessages(activeSession.id, (currentMessages) => [
          ...currentMessages,
          {
            id: crypto.randomUUID(),
            role: "assistant",
            content: "I could not answer that right now. Please try again in a moment.",
            followUps: FOLLOW_UP_QUESTIONS
          }
        ]);
      }
    } finally {
      sendInFlightRef.current = false;
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

  async function startNewChat() {
    if (isCreatingSession || createSessionInFlightRef.current) {
      return;
    }

    createSessionInFlightRef.current = true;
    setIsCreatingSession(true);
    setQuestion("");
    setError(null);

    try {
      await createBackendSession();
      window.setTimeout(() => inputRef.current?.focus(), 0);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to start a new chat.");
    } finally {
      createSessionInFlightRef.current = false;
      setIsCreatingSession(false);
    }
  }

  function switchSession(sessionId: string) {
    setActiveSessionId(sessionId);
    setQuestion("");
    setError(null);
    window.setTimeout(() => inputRef.current?.focus(), 0);
  }

  async function deleteSession(sessionId: string) {
    if (!accessToken) {
      setError("Please sign in again to delete a chat.");
      return;
    }

    const previousSessions = sessions;
    const remainingSessions = sessions.filter((session) => session.id !== sessionId);
    setSessions(remainingSessions);

    if (remainingSessions.length === 0) {
      setActiveSessionId("");
    } else if (sessionId === activeSession?.id) {
      setActiveSessionId(remainingSessions[0].id);
    }

    setQuestion("");
    setError(null);

    try {
      await apiClient.delete(`/chatbot/sessions/${sessionId}`, accessToken);
      window.setTimeout(() => inputRef.current?.focus(), 0);
    } catch (requestError) {
      setSessions(previousSessions);
      setActiveSessionId(activeSession?.id || previousSessions[0]?.id || "");
      setError(requestError instanceof Error ? requestError.message : "Unable to delete this chat.");
    }
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
            onClick={() => void startNewChat()}
            disabled={!accessToken || isCreatingSession}
          >
            {isCreatingSession ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
            New Chat
          </button>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[280px_1fr]">
        <aside className="rounded-md border bg-background p-3">
          <div className="flex items-center justify-between gap-3 border-b pb-3">
            <div>
              <h2 className="text-sm font-semibold">Recent Chats</h2>
              <p className="mt-1 text-xs text-muted-foreground">
                {isSessionLoading && sessions.length === 0
                  ? "Loading chats..."
                  : `${sessions.length} saved session${sessions.length === 1 ? "" : "s"}`}
              </p>
            </div>
            <button
              className="inline-flex h-8 w-8 items-center justify-center rounded-md border text-muted-foreground hover:text-foreground"
              type="button"
              onClick={() => void startNewChat()}
              aria-label="Start new chat"
              disabled={!accessToken || isCreatingSession}
            >
              {isCreatingSession ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
            </button>
          </div>

          <div className="mt-3 max-h-64 space-y-2 overflow-y-auto lg:max-h-[650px]">
            {!isSessionLoading && recentSessions.length === 0 ? (
              <p className="rounded-md border border-dashed px-3 py-4 text-center text-xs text-muted-foreground">
                Start a new chat to save it here.
              </p>
            ) : null}
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
                  onClick={() => void deleteSession(session.id)}
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
            {isSessionLoading && messages.length === 0 ? (
              <div className="flex h-full min-h-72 items-center justify-center">
                <div className="inline-flex items-center gap-2 rounded-md border bg-muted/30 px-4 py-3 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Loading chat...
                </div>
              </div>
            ) : null}

            {!isSessionLoading && messages.length === 0 ? (
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

            {messages.map((message, index) => {
              const isUser = message.role === "user";
              const Icon = isUser ? User : Bot;
              const questionForAssistant = isUser
                ? undefined
                : [...messages.slice(0, index)].reverse().find((previousMessage) => previousMessage.role === "user")?.content;
              const actionLinks = isUser ? [] : actionLinksForMessage(message);
              const sourceCards = isUser ? [] : visibleCardsForMessage(message, questionForAssistant);

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
                        "whitespace-pre-line rounded-md px-4 py-3 text-sm leading-6 shadow-sm",
                        isUser
                          ? "bg-primary text-primary-foreground"
                          : "border bg-muted/40 text-foreground"
                      )}
                    >
                      {message.content}
                    </div>

                    {!isUser && actionLinks.length ? (
                      <div className="flex flex-wrap gap-2">
                        {actionLinks.map((link) => (
                          <a
                            className="inline-flex h-8 items-center gap-2 rounded-md bg-primary px-3 text-xs font-medium text-primary-foreground shadow-sm transition hover:bg-primary/90"
                            href={link.url}
                            key={`${link.label}-${link.url}`}
                            rel="noreferrer"
                            target="_blank"
                          >
                            {link.is_official ? <BadgeCheck className="h-3.5 w-3.5" /> : <ExternalLink className="h-3.5 w-3.5" />}
                            {link.label}
                          </a>
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

                    {!isUser && sourceCards.length ? (
                      <div className="grid gap-2 sm:grid-cols-2">
                        {sourceCards.map((source, index) => (
                          <article
                            className="rounded-md border bg-background p-3 shadow-sm"
                            key={`${source.scheme_id || source.url || source.title || "source"}-${index}`}
                          >
                            <div className="flex items-start justify-between gap-3">
                              <div className="flex min-w-0 items-center gap-2">
                                <FileText className="h-4 w-4 shrink-0 text-primary" />
                                {source.type === "web" && source.verified ? (
                                  <span className="inline-flex shrink-0 items-center gap-1 rounded-md border border-primary/30 bg-primary/5 px-2 py-1 text-[11px] font-medium text-primary">
                                    <BadgeCheck className="h-3 w-3" />
                                    Verified
                                  </span>
                                ) : null}
                              </div>
                              {sourceLink(source) ? (
                                <a
                                  className="inline-flex h-7 shrink-0 items-center gap-1 rounded-md bg-primary px-2 text-xs font-medium text-primary-foreground"
                                  href={sourceLink(source)}
                                  rel="noreferrer"
                                  target="_blank"
                                >
                                  Open Official Source
                                  <ExternalLink className="h-3 w-3" />
                                </a>
                              ) : null}
                            </div>

                            <h3 className="mt-3 line-clamp-2 text-sm font-semibold">
                              {source.title || "Untitled scheme"}
                            </h3>

                            <p className="mt-2 text-xs font-medium text-muted-foreground">
                              {source.type === "web" ? "Official web" : source.category || "Not specified"} /{" "}
                              {source.type === "web" ? "Official source" : source.state || "All India"}
                            </p>
                          </article>
                        ))}
                      </div>
                    ) : null}

                    {!isUser && (message.usedProfile || message.usedWebSearch) ? (
                      <div className="flex flex-wrap gap-2">
                        {message.usedProfile ? (
                          <span className="rounded-md border bg-background px-2 py-1 text-[11px] font-medium text-muted-foreground">
                            Profile-aware
                          </span>
                        ) : null}
                        {message.usedWebSearch ? (
                          <span className="rounded-md border bg-background px-2 py-1 text-[11px] font-medium text-muted-foreground">
                            Official web checked
                          </span>
                        ) : null}
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
                disabled={isLoading || isSessionLoading || !accessToken}
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


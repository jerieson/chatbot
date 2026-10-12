import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { User } from "lucide-react";
import { GengarIcon } from "@/components/GengarIcon";
import { MarkdownMessage } from "@/components/MarkdownMessage";
import type { Message } from "@/types/chat";

interface ChatMessageProps {
  message: Message;
  isUser: boolean;
}

export const ChatMessage = ({ message, isUser }: ChatMessageProps) => {
  return (
    <div className={`flex gap-2 mb-3 ${isUser ? "flex-row-reverse" : ""}`}>
      {isUser ? (
        <Avatar className="h-7 w-7 shrink-0">
          <AvatarFallback className="bg-gengar-900 text-gengar-100">
            <User className="h-3.5 w-3.5" />
          </AvatarFallback>
        </Avatar>
      ) : (
        <GengarIcon className="h-7 w-7" />
      )}

      <div className={`flex flex-col max-w-[80%] ${isUser ? "items-end" : "items-start"}`}>
        <div
          className={`rounded-2xl px-3 py-2 ${
            isUser
              ? "bg-gengar-600 text-white rounded-tr-sm"
              : "bg-gengar-50 text-gengar-950 border border-gengar-100 rounded-tl-sm"
          }`}
        >
          {isUser ? (
            <p className="text-sm leading-relaxed whitespace-pre-wrap wrap-break-word">
              {message.content}
            </p>
          ) : (
            <MarkdownMessage content={message.content} />
          )}
        </div>

        {message.intent && !isUser && (
          <div className="flex items-center gap-1.5 mt-1 px-1">
            <span className="text-[10px] text-gengar-400">
              {new Date(message.timestamp).toLocaleTimeString("en-US", {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </span>
            <Badge variant="outline" className="text-[10px] h-4 px-1.5 border-gengar-200 text-gengar-600">
              {message.intent}
            </Badge>
            {message.confidence !== undefined && (
              <span className="text-[10px] text-gengar-400">
                {(message.confidence * 100).toFixed(0)}%
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

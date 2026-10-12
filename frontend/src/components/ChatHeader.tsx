import { Button } from "@/components/ui/button";
import { Minus } from "lucide-react";
import { GengarIcon } from "@/components/GengarIcon";

interface ChatHeaderProps {
  isOnline?: boolean;
  onMinimize: () => void;
}

export const ChatHeader = ({ isOnline = true, onMinimize }: ChatHeaderProps) => {
  return (
    <div className="flex items-center justify-between gap-2">
      <div className="flex items-center gap-3.5 min-w-0 pl-1">
        <GengarIcon className="h-9 w-9" flames />
        <div className="min-w-0">
          <h2 className="text-sm font-semibold truncate">EY-AY Pokémon Assistant</h2>
          <div className="flex items-center gap-1.5">
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                isOnline ? "bg-green-400 animate-pulse" : "bg-red-400"
              }`}
            />
            <span className="text-xs text-white/70">{isOnline ? "Online" : "Offline"}</span>
          </div>
        </div>
      </div>

      <Button
        variant="ghost"
        size="icon"
        onClick={onMinimize}
        aria-label="Minimize chat"
        className="h-8 w-8 shrink-0 text-white hover:bg-white/15 hover:text-white"
      >
        <Minus className="h-4 w-4" />
      </Button>
    </div>
  );
};

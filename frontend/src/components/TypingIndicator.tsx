import { GengarIcon } from "@/components/GengarIcon";

export const TypingIndicator = () => {
  return (
    <div className="flex gap-2 mb-3">
      <GengarIcon className="h-7 w-7" flames />
      <div className="bg-gengar-50 border border-gengar-100 rounded-2xl rounded-tl-sm px-4 py-3">
        <div className="flex gap-1.5">
          <div
            className="w-2 h-2 bg-gengar-400 rounded-full animate-bounce"
            style={{ animationDelay: "0ms" }}
          />
          <div
            className="w-2 h-2 bg-gengar-400 rounded-full animate-bounce"
            style={{ animationDelay: "150ms" }}
          />
          <div
            className="w-2 h-2 bg-gengar-400 rounded-full animate-bounce"
            style={{ animationDelay: "300ms" }}
          />
        </div>
      </div>
    </div>
  );
};

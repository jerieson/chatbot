import ReactMarkdown, { type Components } from "react-markdown";
import remarkBreaks from "remark-breaks";
import remarkGfm from "remark-gfm";

// Bot replies can contain Markdown (LLM answers, guide sections). react-markdown
// never renders raw HTML, so replies cannot inject markup into the page.
const components: Components = {
  p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
  strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
  ul: ({ children }) => <ul className="list-disc pl-4 mb-2 last:mb-0 space-y-0.5">{children}</ul>,
  ol: ({ children }) => <ol className="list-decimal pl-4 mb-2 last:mb-0 space-y-0.5">{children}</ol>,
  h1: ({ children }) => <p className="font-semibold mb-1">{children}</p>,
  h2: ({ children }) => <p className="font-semibold mb-1">{children}</p>,
  h3: ({ children }) => <p className="font-semibold mb-1">{children}</p>,
  a: ({ children, href }) => (
    <a href={href} target="_blank" rel="noopener noreferrer" className="underline text-gengar-700">
      {children}
    </a>
  ),
  code: ({ children }) => (
    <code className="rounded bg-gengar-100 px-1 py-0.5 font-mono text-[0.85em]">{children}</code>
  ),
  table: ({ children }) => (
    <div className="overflow-x-auto mb-2 last:mb-0">
      <table className="text-left border-collapse">{children}</table>
    </div>
  ),
  th: ({ children }) => <th className="border-b border-gengar-200 px-2 py-1 font-semibold">{children}</th>,
  td: ({ children }) => <td className="border-b border-gengar-100 px-2 py-1">{children}</td>,
};

export const MarkdownMessage = ({ content }: { content: string }) => (
  <div className="text-sm leading-relaxed wrap-break-word">
    <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]} components={components}>
      {content}
    </ReactMarkdown>
  </div>
);

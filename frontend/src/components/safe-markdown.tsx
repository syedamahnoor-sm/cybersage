import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
/** No raw HTML, remote images or actionable links from generated/untrusted content. */
export function SafeMarkdown({ children }: { children: string }) {
  return (
    <div className="markdown">
      <ReactMarkdown
        skipHtml
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ children }) => <span>{children}</span>,
          img: () => null,
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}

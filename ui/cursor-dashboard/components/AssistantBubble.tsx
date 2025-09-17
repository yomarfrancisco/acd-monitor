import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import rehypeHighlight from 'rehype-highlight';

// CSS for highlight theme (KaTeX CSS imported globally in layout.tsx)
import 'highlight.js/styles/github-dark-dimmed.css';

export function AssistantBubble({ text }: { text: string }) {
  return (
    <div className="assistant-bubble">
      <div className="assistant-md lg:text-base lg:leading-5">
        <ReactMarkdown
          remarkPlugins={[remarkGfm, remarkMath]}
          rehypePlugins={[
            [rehypeKatex, { output: 'html' }],
            // auto-detects language; if perf becomes an issue, we can restrict languages
            rehypeHighlight
          ]}
          components={{
            a: (props) => <a {...props} target="_blank" rel="noopener noreferrer" />,
            // keep headings the same size as your current bubble (no giant h1/h2)
            h1: ({children}) => <strong>{children}</strong>,
            h2: ({children}) => <strong>{children}</strong>,
            h3: ({children}) => <strong>{children}</strong>,
          }}
        >
          {text}
        </ReactMarkdown>
      </div>
    </div>
  );
}

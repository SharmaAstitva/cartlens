import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useNavigate } from "react-router";

/** Ctrl/⌘ + K opens a quick switcher: type to filter, ↑ ↓ to choose, Enter to go, Esc to close. */
export default function CommandPalette({ items }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const input = useRef(null);
  const navigate = useNavigate();

  const show = () => {
    setQuery("");
    setActive(0);
    setOpen(true);
  };

  useEffect(() => {
    const onKey = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setQuery("");
        setActive(0);
        setOpen((o) => !o);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (open) input.current.focus();
  }, [open]);

  const q = query.trim().toLowerCase();
  const matches = items.filter((it) => `${it.label} ${it.hint}`.toLowerCase().includes(q));
  const go = (item) => {
    setOpen(false);
    navigate(item.path);
  };
  const onKeyDown = (e) => {
    if (e.key === "Escape") setOpen(false);
    else if (e.key === "ArrowDown") setActive((a) => Math.min(a + 1, matches.length - 1));
    else if (e.key === "ArrowUp") setActive((a) => Math.max(a - 1, 0));
    else if (e.key === "Enter" && matches[active]) go(matches[active]);
    else return;
    e.preventDefault();
  };

  return (
    <>
      <button type="button" className="palette-trigger" onClick={show}>
        <span>Jump to</span>
        <kbd>Ctrl K</kbd>
      </button>
      {open &&
        createPortal(
          <div className="palette-backdrop" onMouseDown={() => setOpen(false)}>
            <div
              className="palette"
              role="dialog"
              aria-modal="true"
              aria-label="Jump to a page"
              onMouseDown={(e) => e.stopPropagation()}
            >
              <input
                ref={input}
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setActive(0);
                }}
                onKeyDown={onKeyDown}
                placeholder="Type a page name"
                aria-label="Search pages"
                aria-controls="palette-list"
                aria-activedescendant={matches[active] ? `palette-${matches[active].path}` : undefined}
                role="combobox"
                aria-expanded="true"
              />
              <ul id="palette-list" role="listbox" aria-label="Pages">
                {matches.map((it, i) => (
                  <li
                    key={it.path}
                    id={`palette-${it.path}`}
                    role="option"
                    aria-selected={i === active}
                    onMouseEnter={() => setActive(i)}
                    onClick={() => go(it)}
                  >
                    <span>{it.label}</span>
                    <span className="muted">{it.hint}</span>
                  </li>
                ))}
                {matches.length === 0 && <li className="muted palette-empty">No page matches “{query}”.</li>}
              </ul>
            </div>
          </div>,
          document.body,
        )}
    </>
  );
}

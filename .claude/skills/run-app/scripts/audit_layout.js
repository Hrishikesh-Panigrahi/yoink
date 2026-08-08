/* Find elements that overflow their box or escape their parent.
 *
 * Feed this to cdp.py as one expression (it returns an array of strings):
 *
 *   python -c "import json,pathlib; json.dump([pathlib.Path('audit_layout.js').read_text()], open('a.json','w'))"
 *   python cdp.py a.json --timeout-ms 8000
 *
 * Switch views and open modals between runs - it only sees what is rendered.
 *
 * Two classes of bug it catches, both of which shipped in this UI at some
 * point and neither of which is obvious by eye until a title happens to be
 * long enough:
 *
 *   SELF-OVERFLOW   content wider than the box, with no scrolling allowed.
 *   ESCAPES-PARENT  a child sticking out past its parent's right edge, which
 *                   is what a grid or flex item does when it cannot shrink
 *                   (the default min-width is `auto`, not 0).
 *
 * `.sr-only` elements are skipped: they are deliberately clipped to 1px for
 * screen readers and are not layout bugs.
 */
(() => {
  const findings = [];
  const seen = new Set();

  const describe = (el) =>
    el.tagName.toLowerCase() +
    (el.id ? "#" + el.id : "") +
    (el.className && typeof el.className === "string"
      ? "." + el.className.trim().split(/\s+/).slice(0, 2).join(".")
      : "");

  document.querySelectorAll("body *").forEach((el) => {
    if (!el.getClientRects().length) return;
    if (el.classList && el.classList.contains("sr-only")) return;
    const cs = getComputedStyle(el);
    if (cs.visibility === "hidden" || cs.display === "none") return;

    const name = describe(el);

    if (!/auto|scroll/.test(cs.overflowX) && el.clientWidth > 0 &&
        el.scrollWidth > el.clientWidth + 1) {
      const key = "SELF " + name;
      if (!seen.has(key)) {
        seen.add(key);
        findings.push(
          `SELF-OVERFLOW   ${name}  content ${el.scrollWidth} > box ${el.clientWidth}`);
      }
    }

    const parent = el.parentElement;
    if (parent && parent !== document.body &&
        !/auto|scroll/.test(getComputedStyle(parent).overflowX)) {
      const a = el.getBoundingClientRect();
      const b = parent.getBoundingClientRect();
      const over = Math.round(a.right - b.right);
      if (over > 1) {
        const key = "ESC " + name;
        if (!seen.has(key)) {
          seen.add(key);
          findings.push(
            `ESCAPES-PARENT  ${name}  ${over}px past ${describe(parent)}`);
        }
      }
    }
  });

  return findings.length ? findings.slice(0, 25) : ["clean"];
})()

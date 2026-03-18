/**
 * Lightweight Python syntax highlighter for the Cool Linen editor.
 * Returns an HTML string with <span> wrappers for token classes.
 *
 * Token classes (styled in globals.css):
 *   .py-kw      keywords          #993333 bold
 *   .py-str     strings           #6a7b3a
 *   .py-cmt     comments          #a3a3a3 italic
 *   .py-fn      function names    #5a6f8f
 *   .py-num     numbers           #b35c00
 *   .py-dec     decorators        #8b6bb3
 *   .py-bi      builtins          #737373
 */

const KEYWORDS = new Set([
  'False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await',
  'break', 'class', 'continue', 'def', 'del', 'elif', 'else', 'except',
  'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is',
  'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return', 'try',
  'while', 'with', 'yield',
])

const BUILTINS = new Set([
  'abs', 'all', 'any', 'bin', 'bool', 'bytes', 'callable', 'chr',
  'classmethod', 'complex', 'dict', 'dir', 'divmod', 'enumerate',
  'eval', 'filter', 'float', 'format', 'frozenset', 'getattr',
  'globals', 'hasattr', 'hash', 'hex', 'id', 'input', 'int',
  'isinstance', 'issubclass', 'iter', 'len', 'list', 'locals', 'map',
  'max', 'min', 'next', 'object', 'oct', 'open', 'ord', 'pow',
  'print', 'property', 'range', 'repr', 'reversed', 'round', 'set',
  'setattr', 'slice', 'sorted', 'staticmethod', 'str', 'sum', 'super',
  'tuple', 'type', 'vars', 'zip',
  // numpy/scipy/torch common
  'np', 'pd', 'torch', 'tf', 'nn', 'F',
  'self',
])

function esc(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

// Ordered token patterns — first match wins
const TOKEN_RE = new RegExp([
  // triple-quoted strings (greedy across lines handled per-line, so keep simple)
  `("""(?:[^"\\\\]|\\\\.)*?"""|'''(?:[^'\\\\]|\\\\.)*?''')`,
  // single-line strings
  `(f?"(?:[^"\\\\]|\\\\.)*"|f?'(?:[^'\\\\]|\\\\.)*')`,
  // comments
  `(#.*)`,
  // decorators
  `(@\\w+)`,
  // numbers (floats, ints, hex, scientific)
  `(\\b(?:0[xXoObB][\\da-fA-F_]+|\\d[\\d_]*\\.?[\\d_]*(?:[eE][+-]?\\d+)?)\\b)`,
  // identifiers (keywords, builtins, function names handled in callback)
  `(\\b[A-Za-z_]\\w*\\b)`,
].join('|'), 'g')

export function highlightPython(code: string): string {
  let expectFnName = false
  let result = ''
  let lastIndex = 0

  // Reset regex state for each call
  TOKEN_RE.lastIndex = 0
  let m: RegExpExecArray | null
  while ((m = TOKEN_RE.exec(code)) !== null) {
    // Escape any plain text between the previous match and this one
    if (m.index > lastIndex) {
      result += esc(code.substring(lastIndex, m.index))
    }
    lastIndex = TOKEN_RE.lastIndex

    const [, tripleStr, singleStr, comment, decorator, number, ident] = m

    if (tripleStr)  { expectFnName = false; result += `<span class="py-str">${esc(tripleStr)}</span>`; continue }
    if (singleStr)  { expectFnName = false; result += `<span class="py-str">${esc(singleStr)}</span>`; continue }
    if (comment)    { result += `<span class="py-cmt">${esc(comment)}</span>`; continue }
    if (decorator)  { expectFnName = false; result += `<span class="py-dec">${esc(decorator)}</span>`; continue }
    if (number)     { expectFnName = false; result += `<span class="py-num">${esc(number)}</span>`; continue }
    if (ident) {
      if (expectFnName) {
        expectFnName = false
        result += `<span class="py-fn">${esc(ident)}</span>`
      } else if (ident === 'def' || ident === 'class') {
        expectFnName = true
        result += `<span class="py-kw">${esc(ident)}</span>`
      } else if (KEYWORDS.has(ident)) {
        result += `<span class="py-kw">${esc(ident)}</span>`
      } else if (BUILTINS.has(ident)) {
        result += `<span class="py-bi">${esc(ident)}</span>`
      } else {
        result += esc(ident)
      }
    }
  }

  // Escape any remaining text after the last match
  if (lastIndex < code.length) {
    result += esc(code.substring(lastIndex))
  }

  return result
}

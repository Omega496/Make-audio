"""
Markdown and Document Cleaning Module for Text-to-Speech (TTS).

Converts markdown, plain text, and extracted PDF documents into natural,
fluent plain English suitable for Kokoro-TTS narration.
Handles:
- LaTeX math formulas, Greek letters, physics symbols, operators, matrices, and units
- Currency expressions ($100, $5.50)
- Tables converted to natural spoken sentences
- Code blocks, Mermaid diagrams, and ASCII art
- HTML tags, media elements (<svg>, <video>, <audio>), <summary>/<details>, <progress>, <meter>
- GitHub alert callouts (> [!NOTE], > [!WARNING], etc.)
- Checklists / tasks ([-*] [x], [-*] [ ])
- Footnotes ([^1], ^[1]:)
- Markdown links, images, bold, italics, strikethrough, headers, and bullet lists
- Unicode emojis and control characters
- Paragraph pacing and sentence-boundary chunking
"""

import html
import re
import unicodedata
from typing import List, Optional


# ---------------------------------------------------------------------------
# Greek & Mathematical Pronunciation Dictionaries
# ---------------------------------------------------------------------------
GREEK_LETTERS = {
    'alpha': 'alpha', 'beta': 'beta', 'gamma': 'gamma', 'delta': 'delta',
    'epsilon': 'epsilon', 'varepsilon': 'epsilon', 'zeta': 'zeta', 'eta': 'eta',
    'theta': 'theta', 'vartheta': 'theta', 'iota': 'iota', 'kappa': 'kappa',
    'lambda': 'lambda', 'mu': 'mu', 'nu': 'nu', 'xi': 'xi', 'pi': 'pi',
    'varpi': 'pi', 'rho': 'rho', 'varrho': 'rho', 'sigma': 'sigma',
    'varsigma': 'sigma', 'tau': 'tau', 'upsilon': 'upsilon', 'phi': 'phi',
    'varphi': 'phi', 'chi': 'chi', 'psi': 'psi', 'omega': 'omega',
    'Gamma': 'Gamma', 'Delta': 'Delta', 'Theta': 'Theta', 'Lambda': 'Lambda',
    'Xi': 'Xi', 'Pi': 'Pi', 'Sigma': 'Sigma', 'Upsilon': 'Upsilon',
    'Phi': 'Phi', 'Psi': 'Psi', 'Omega': 'Omega',
}

MATH_RELATIONS = [
    (r'\\leq\b|\\le\b', ' is less than or equal to '),
    (r'\\geq\b|\\ge\b', ' is greater than or equal to '),
    (r'\\neq\b|\\ne\b', ' is not equal to '),
    (r'\\approx\b', ' is approximately '),
    (r'\\simeq\b', ' is approximately '),
    (r'\\sim\b', ' is roughly '),
    (r'\\ll\b', ' is much less than '),
    (r'\\gg\b', ' is much greater than '),
    (r'\\pm\b', ' plus or minus '),
    (r'\\mp\b', ' minus or plus '),
    (r'\\times\b', ' times '),
    (r'\\cdot\b', ' dot '),
    (r'\\div\b', ' divided by '),
    (r'\\propto\b', ' is proportional to '),
    (r'\\implies\b', ' implies that '),
    (r'\\iff\b', ' if and only if '),
    (r'\\longleftrightarrow\b', ' in equilibrium with '),
    (r'\\to\b|\\rightarrow\b', ' approaches '),
    (r'\\leftarrow\b', ' left arrow '),
    (r'\\forall\b', ' for all '),
    (r'\\exists\b', ' there exists '),
    (r'\\notin\b', ' is not in '),
    (r'\\in\b', ' in '),
    (r'\\subset\b', ' is a subset of '),
    (r'\\cup\b', ' union '),
    (r'\\cap\b', ' intersection '),
    (r'\\infty\b', ' infinity '),
]

MATH_OPERATORS = [
    (r'\\nabla\^2', ' Laplacian '),
    (r'\\vec\{\\nabla\}|\\vec{\\nabla}|\{\\vec\\nabla\}|\\vec\s*\\nabla', ' gradient '),
    (r'\\nabla', ' del '),
    (r'\\partial', ' partial '),
    (r'\\det\b', ' determinant of '),
    (r'\\text\{tr\}\b|\\operatorname\{tr\}\b', ' trace of '),
    (r'\\log\b', ' log '),
    (r'\\ln\b', ' natural log of '),
    (r'\\exp\b', ' exp '),
    (r'\\sin\b', ' sine '),
    (r'\\cos\b', ' cosine '),
    (r'\\tan\b', ' tangent '),
    (r'M_\\odot|M_\\odot\b|M_\{\\odot\}|\\text\{M\}_\{\\odot\}', ' solar masses '),
    (r'\\odot', ' sun '),
    (r'\\quad|\\qquad', ' , '),
]


def is_ascii_diagram(text: str) -> bool:
    """
    Detect if a block of text is an ASCII art / diagram rather than plain text or code.
    Checks for high frequency of drawing characters (^, |, \\, +, --, -->, etc.).
    """
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return False

    diagram_chars = set("|^\\+<>_~`/-")
    drawing_count = 0
    alpha_count = 0

    for line in lines:
        # Check for typical diagram patterns
        if re.search(r'\+[-=]{3,}\+', line):
            return True
        if re.search(r'\|.*\\.*\|', line):
            return True
        if re.search(r'^\s*[\^\|]\s*$', line):
            return True
        if re.search(r'[-=]{2,}>', line):
            return True
        if re.search(r'\<[-=]{2,}', line):
            return True
        if re.search(r'^\s*[\|\+]\s+.*[\|\+]$', line):
            return True

        for ch in line:
            if ch in diagram_chars:
                drawing_count += 1
            elif ch.isalpha():
                alpha_count += 1

    total = drawing_count + alpha_count
    if total > 0 and (drawing_count / total > 0.20):
        return True

    return False


def clean_math_to_spoken(expr: str) -> str:
    """
    Convert mathematical / scientific expressions into spoken plain English.
    """
    s = expr.strip()
    if s.startswith('$$') and s.endswith('$$'):
        s = s[2:-2].strip()
    elif s.startswith('$') and s.endswith('$'):
        s = s[1:-1].strip()

    # 1. Specific units, astrophysics and chemistry constants
    s = re.sub(r'1\\,\s*\\text\{rad\}\s*\\approx\s*206,?265\'\'', '1 radian is approximately 206,265 arcseconds', s)
    s = re.sub(r'(\d+)\'\'', r'\1 arcseconds', s)
    s = re.sub(r'(\d+)\'', r'\1 arcminutes', s)
    s = re.sub(r'\\text\{H\}_2\\text\{O\}|H_2O', 'H 2 O', s)
    s = re.sub(r'E\s*=\s*mc\^2', 'E equals m c squared', s)

    # Specific unit and quantity substitutions first
    replacements = [
        # Units with division/powers
        (r'\\text\{GeV\}/c\^2|GeV/c\^2', 'GeV per c squared'),
        (r'\\text\{TeV\}/c\^2|TeV/c\^2', 'TeV per c squared'),
        (r'\\text\{keV\}/c\^2|keV/c\^2', 'keV per c squared'),
        (r'\\text\{MeV\}/c\^2|MeV/c\^2', 'MeV per c squared'),
        (r'\\text\{cm\}\^3/\\text\{s\}|cm\^3/s', 'cubic centimeters per second'),
        (r'\\text\{km\}/\\text\{s\}|km/s', 'kilometers per second'),

        # Simple text units
        (r'\\text\{GeV\}', ' GeV'),
        (r'\\text\{TeV\}', ' TeV'),
        (r'\\text\{MeV\}', ' MeV'),
        (r'\\text\{keV\}', ' keV'),
        (r'\\text\{eV\}', ' electron volts'),
        (r'\\text\{m\}', ' meters'),
        (r'\\text\{s\}', ' seconds'),
        (r'\\text\{NFW\}', 'NFW'),
        (r'\\text\{SM\}', 'Standard Model'),
        (r'\\text\{WIMP\}', 'WIMP'),
        (r'\\text\{DM\}', 'dark matter'),

        # Physics / Cosmology symbols and expressions
        (r'\\Lambda\\text\{CDM\}|\\Lambda\s*CDM', 'Lambda CDM'),
        (r'E_T\^\{\\text\{miss\}\}|E_T\^\{miss\}', 'missing transverse energy'),
        (r'\\langle\s*\\sigma\s*v\s*\\rangle', 'sigma v'),
        (r'\\Omega_\\chi\s*h\^2|\\Omega_chi\s*h\^2', 'Omega chi h squared'),
        (r'\\Omega_\\text\{DM\}\s*h\^2|\\Omega_\{DM\}\s*h\^2|\\Omega_DM\s*h\^2', 'Omega dark matter h squared'),
        (r'\\Omega_\\text\{DM\}|\\Omega_\{DM\}|\\Omega_DM', 'Omega dark matter'),
        (r'\\Omega_\\chi|\\Omega_chi', 'Omega chi'),
        (r'\\rho_\\text\{NFW\}|\\rho_\{NFW\}|\\rho_NFW', 'rho NFW'),
        (r'\\rho_0', 'rho zero'),
        (r'r_s', 'r sub s'),
        (r'm_\\chi|m_chi', 'm sub chi'),
        (r'n_\\chi|n_chi', 'n sub chi'),
        (r'\\Gamma_\\text\{ann\}|\\Gamma_\{ann\}', 'annihilation rate Gamma'),
        (r'W\^\\pm/Z', 'W plus-or-minus or Z bosons'),
        (r'\\overline\{\\text\{WIMP\}\}|\\overline\{WIMP\}', 'anti-WIMP'),
        (r'N\s*-\s*Body', 'N-Body'),

        # Common variables
        (r'\bm\s*~', 'mass approximately '),
        (r'\bT\s*<', 'temperature less than '),
    ]
    for pattern, repl in replacements:
        s = re.sub(pattern, repl, s)

    # 2. Matrices & Cases
    if r'\begin{pmatrix}' in s or r'\begin{bmatrix}' in s or r'\begin{matrix}' in s or r'\begin{vmatrix}' in s:
        match = re.search(r'(\\mathbf\{?([A-Za-z])\}?|\\mathcal\{?([A-Za-z])\}?|\b([A-Za-z])\b)\s*=', s)
        name = match.group(2) or match.group(3) or match.group(4) if match else ""
        return f"Matrix {name}" if name else "the matrix shown in the document"

    if r'\begin{cases}' in s:
        match = re.search(r'([A-Za-z]\s*\([^)]*\))\s*=', s)
        func = match.group(1) if match else "f of x"
        return f"piecewise function {func}"

    if r'\begin{aligned}' in s or r'\begin{align}' in s:
        s = re.sub(r'\\begin\{aligned\}|\\end\{aligned\}|\\begin\{align\*?\}|\\end\{align\*?\}', '', s)
        s = s.replace('&', ' ').replace(r'\\', ' . ')

    # 3. Fonts and Text Wrappers
    s = re.sub(r'\\(text|mathrm|mathbf|mathcal|operatorname|mathit)\{([^}]+)\}', r' \2 ', s)

    # 4. Calculus (Limits, Integrals, Sums, Partials)
    s = re.sub(r'\\lim_\{([^{}]+)\\to\s*([^{}]+)\}', r'the limit as \1 approaches \2 of ', s)
    s = re.sub(r'\\int_\{([^}]+)\}\^\{([^}]+)\}', r'the integral from \1 to \2 of ', s)
    s = re.sub(r'\\int', 'the integral of ', s)
    s = re.sub(r'\\sum_\{([^}]+)\}\^\{([^}]+)\}', r'the sum from \1 to \2 of ', s)
    s = re.sub(r'\\sum', 'the sum of ', s)
    s = re.sub(r'\\frac\{\\partial\s*([A-Za-z])\}\{\\partial\s*([A-Za-z])\}', r'partial \1 over partial \2', s)

    # 5. Fractions (up to 5 nested levels)
    for _ in range(5):
        if r'\frac' not in s:
            break
        s = re.sub(r'\\frac\{([^{}]+)\}\{([^{}]+)\}', r'(\1 over \2)', s)
    s = re.sub(r'\\frac\s*\{?([a-zA-Z0-9]+)\}?\s*\{?([a-zA-Z0-9]+)\}?', r'(\1 over \2)', s)

    # 6. Roots
    for _ in range(3):
        if r'\sqrt' not in s:
            break
        s = re.sub(r'\\sqrt\[([^\]]+)\]\{([^{}]+)\}', r'the \1 root of \2', s)
        s = re.sub(r'\\sqrt\{([^{}]+)\}', r'the square root of (\1)', s)

    # 7. Parentheses and Braces Delimiters
    s = re.sub(r'\\left\(|\\right\)', ' ', s)
    s = re.sub(r'\\left\[|\\right\]', ' ', s)
    s = re.sub(r'\\left\\\{|\\right\\\}', ' ', s)
    s = re.sub(r'\\left\||\\right\|', ' ', s)

    # 8. Math Operators and Relations
    for pat, rep in MATH_OPERATORS:
        s = re.sub(pat, rep, s)
    for pat, rep in MATH_RELATIONS:
        s = re.sub(pat, rep, s)

    # 9. Greek Letters
    for greek, spoken in GREEK_LETTERS.items():
        s = re.sub(rf'\\{greek}\b', f' {spoken} ', s)

    # 10. Vector and Accent Decorators
    s = re.sub(r'\\vec\{([^}]+)\}', r'\1 vector', s)
    s = re.sub(r'\\hat\{([^}]+)\}', r'\1 hat', s)
    s = re.sub(r'\\bar\{([^}]+)\}', r'\1 bar', s)
    s = re.sub(r'\\tilde\{([^}]+)\}', r'\1 tilde', s)
    s = re.sub(r'\\dot\{([^}]+)\}', r'\1 dot', s)

    # 11. Powers and Exponents
    s = re.sub(r'10\^\{-(\d+)\}|10\^-(\d+)', r'10 to the minus \1\2', s)
    s = re.sub(r'10\^\{(\d+)\}|10\^(\d+)', r'10 to the \1\2', s)
    s = re.sub(r'r\^\{-1\}|r\^-1', 'r to the minus 1', s)
    s = re.sub(r'r\^0', 'r to the power of 0', s)
    s = re.sub(r'\^2\b|\^\{2\}', ' squared ', s)
    s = re.sub(r'\^3\b|\^\{3\}', ' cubed ', s)
    s = re.sub(r'\^\{([^{}]+)\}', r' to the power of \1 ', s)
    s = re.sub(r'\^([0-9a-zA-Z])', r' to the power of \1 ', s)

    # 12. Subscripts
    def clean_sub(m):
        c = m.group(1).replace('_', ' ').strip()
        if c == 'cr': return ' critical'
        if c == 'rel': return ' relative'
        if c == 'ext': return ' external'
        if c == 'ls': return ' l s'
        if c == 'E': return ' E'
        return f' {c}'
    s = re.sub(r'_\{([^{}]+)\}', clean_sub, s)
    s = re.sub(r'_([0-9a-zA-Z])', r' \1', s)

    # 13. Clean remaining LaTeX markers
    s = re.sub(r'\\[a-zA-Z]+', ' ', s)
    s = re.sub(r'[{}]', '', s)
    s = s.replace('=', ' equals ')
    s = s.replace('+', ' plus ')
    s = s.replace('-', ' minus ')
    s = s.replace(r'\,', ' ')
    s = s.replace('&', ' and ')
    s = s.replace('|', ' ')

    # 14. Expand standalone units attached to numbers
    s = re.sub(r'(\b\d+(?:\.\d+)?\s*)eV\b', r'\1 electron volts', s)
    s = re.sub(r'(\b\d+(?:\.\d+)?\s*)m\b', r'\1 meters', s)
    s = re.sub(r'(\b\d+(?:\.\d+)?\s*)cm\b', r'\1 centimeters', s)
    s = re.sub(r'(\b\d+(?:\.\d+)?\s*)km\b', r'\1 kilometers', s)
    s = re.sub(r'(\b\d+(?:\.\d+)?\s*)s\b', r'\1 seconds', s)

    s = re.sub(r'\s+', ' ', s).strip()
    return s


def convert_markdown_table_to_sentences(table_block: str) -> str:
    """
    Convert a Markdown table into spoken, natural English paragraphs.
    """
    lines = [line.strip() for line in table_block.strip().split('\n') if line.strip()]
    if len(lines) < 2:
        return ""

    # Locate separator line (e.g. |---|---|)
    sep_idx = -1
    for i, line in enumerate(lines):
        if re.match(r'^\|?(\s*:?-+:?\s*\|)+\s*:?-+:?\s*\|?$', line):
            sep_idx = i
            break

    if sep_idx == -1:
        data_rows = lines
    else:
        data_rows = lines[sep_idx + 1:]

    spoken_rows = []
    for row in data_rows:
        cols = [c.strip() for c in row.split('|') if c.strip()]
        if not cols:
            continue

        first = cols[0]
        cleaned_cols = []
        for c in cols[1:]:
            c_clean = c.rstrip('. ')
            if c_clean:
                cleaned_cols.append(c_clean)

        if cleaned_cols:
            body = '. '.join(cleaned_cols)
            spoken_rows.append(f"{first}: {body}.")
        else:
            spoken_rows.append(f"{first}.")

    return '\n\n'.join(spoken_rows)


def remove_emojis(text: str) -> str:
    """
    Remove emojis and graphical icons that disrupt TTS.
    """
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001F900-\U0001F9FF"  # supplemental symbols
        "\U0001FA00-\U0001FA6F"  # chess, symbols
        "\U0001FA70-\U0001FAFF"  # symbols and pictographs extended-a
        "\U00002600-\U000026FF"  # misc symbols
        "\U00002300-\U000023FF"  # misc technical
        "]+",
        flags=re.UNICODE
    )
    return emoji_pattern.sub('', text)


def clean_markdown_for_tts(
    markdown_text: str,
    remove_display_equations: bool = True,
    drop_code: bool = False,
    code_placeholder: str = "Please refer to the code block shown in the document.",
    diagram_placeholder: str = "Please refer to the diagram shown in the document.",
) -> str:
    """
    Clean markdown or text for TTS narration:
    - Normalizes line endings and removes control characters / replacement chars
    - Strips YAML frontmatter
    - Strips HTML comments, media elements (<svg>, <video>, <audio>), <summary>/<details>, <progress>, <meter>
    - Converts currency ($100, $5.50) before LaTeX math processing
    - Strips or converts LaTeX math to plain English (display and inline)
    - Removes citations ([1], [1-5], (e.g. [6])) and footnotes ([^1])
    - Converts tables to natural spoken sentences
    - Strips or explains code blocks and Mermaid diagrams
    - Handles GitHub callouts (> [!NOTE], etc.) and task checklists
    - Expands inline code identifiers (removing underscores, pronouncing .py, .ipynb)
    - Strips markdown formatting (headers, blockquotes, bullets, links, bold/italics, strikethrough)
    - Deduplicates repeated phrases in parentheses
    - Normalizes punctuation and whitespace
    - Paces paragraphs with sentence-boundary chunking
    """
    text = markdown_text.replace('\r\n', '\n').replace('\r', '\n')

    # 1. Strip YAML frontmatter if present
    text = re.sub(r'^---\s*\n.*?\n---\s*\n', '', text, flags=re.DOTALL)

    # 2. Strip HTML comments, control characters, and replacement chars
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
    text = re.sub(r'[\ufffd\x00-\x08\x0b\x0c\x0e-\x1f\x7f]+', '', text)

    # 3. Strip HTML media elements (<svg>, <video>, <audio>)
    text = re.sub(r'<svg\b[^>]*>.*?</svg>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<video\b[^>]*>.*?</video>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<audio\b[^>]*>.*?</audio>', '', text, flags=re.DOTALL | re.IGNORECASE)

    # 4. Handle HTML <summary>, <details>, <progress>, <meter>
    text = re.sub(r'<summary\b[^>]*>(.*?)</summary>', r'\n\1\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</?details\b[^>]*>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<progress[^>]*value="([^"]+)"[^>]*>.*?</progress>', r'\1 percent', text, flags=re.IGNORECASE)
    text = re.sub(r'<meter[^>]*value="([^"]+)"[^>]*>(.*?)</meter>', r'\2', text, flags=re.IGNORECASE)

    # 5. Nested image links and standalone images
    text = re.sub(r'\[!\[.*?\]\(.*?\)\]\(.*?\)', '', text)
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)

    # 6. Currency expressions ($100, $5.50) BEFORE LaTeX math parsing
    text = re.sub(r'\$(\d+)\.(\d{2})\b', r'\1 dollars and \2 cents', text)
    text = re.sub(r'\$(\d+)\b', r'\1 dollars', text)

    # 7. Handle Display Math ($$...$$ and \[...\])
    if remove_display_equations:
        # If display math follows a colon at the end of a sentence, change the colon to a period
        text = re.sub(r':[ \t]*\n[ \t]*\$\$[\s\S]*?\$\$', '.\n\n', text)
        text = re.sub(r'\$\$[\s\S]*?\$\$', '\n\n', text)
        text = re.sub(r':[ \t]*\n[ \t]*\\\[[\s\S]*?\\\]', '.\n\n', text)
        text = re.sub(r'\\\[[\s\S]*?\\\]', '\n\n', text)
    else:
        def _spoken_display_math(m):
            spoken = clean_math_to_spoken(m.group(1))
            return f"\n\n{spoken}.\n\n" if spoken else ""
        text = re.sub(r'\$\$([\s\S]*?)\$\$', _spoken_display_math, text)
        text = re.sub(r'\\\[([\s\S]*?)\\\]', _spoken_display_math, text)

    # 8. Handle Inline Math ($...$ and \(...\))
    def handle_inline_math(m):
        inner = m.group(1)
        spoken = clean_math_to_spoken(inner)
        return f" {spoken} " if spoken else ""

    text = re.sub(r'(?<!\$)\$(?!\$)([^\$\n]+?)(?<!\$)\$(?!\$)', handle_inline_math, text)
    text = re.sub(r'\\\(([^)]+)\\\)', handle_inline_math, text)
    # Strip any stray dollar signs
    text = text.replace('$', '')

    # 9. Handle Code Blocks and Diagrams (``` and ~~~)
    def handle_code_block(m):
        lang = (m.group(1) or "").strip().lower()
        code_content = m.group(2) or ""
        if lang == 'mermaid' or is_ascii_diagram(code_content):
            return f"\n\n{diagram_placeholder}\n\n" if diagram_placeholder else "\n\n"
        if drop_code:
            return ""
        clean_lines = [l.strip() for l in code_content.splitlines() if l.strip()]
        if len(clean_lines) <= 4 and not any(ch in code_content for ch in "{}()<>=;"):
            return '\n\n' + '. '.join(clean_lines) + '.\n\n'
        return f"\n\n{code_placeholder}\n\n" if code_placeholder else "\n\n"

    text = re.sub(r'```([a-zA-Z0-9_-]*)\n([\s\S]*?)```', handle_code_block, text)
    text = re.sub(r'~~~([a-zA-Z0-9_-]*)\n([\s\S]*?)~~~', handle_code_block, text)
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)

    # 10. Convert Markdown Tables into spoken sentences
    table_pattern = re.compile(r'(?:^[ \t]*\|.*\|[ \t]*$\n?)+', re.MULTILINE)
    text = table_pattern.sub(lambda m: convert_markdown_table_to_sentences(m.group(0)), text)

    # 11. GitHub-style Alert Callouts (> [!NOTE], > [!WARNING], etc.)
    text = re.sub(r'^\s*>\s*\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]', r'\1:', text, flags=re.MULTILINE | re.IGNORECASE)

    # 12. Checklists / Tasks
    text = re.sub(r'^\s*[-*]\s*\[x\]\s*', 'Completed: ', text, flags=re.MULTILINE | re.IGNORECASE)
    text = re.sub(r'^\s*[-*]\s*\[\s*\]\s*', 'Task: ', text, flags=re.MULTILINE)

    # 13. Strip remaining HTML tags and decode HTML entities
    text = re.sub(r'</?[a-zA-Z][a-zA-Z0-9]*(?:\s+[^>]*)?/?>', ' ', text)
    text = html.unescape(text)

    # 14. Academic Citations & Footnotes
    text = re.sub(r'\(\s*(?:e\.g\.|see)\s*\[[\d\s,–\-—]+\]\s*\)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^\s*\[\^[0-9]+\]:\s*', 'Footnote: ', text, flags=re.MULTILINE)
    text = re.sub(r'\[\^[0-9]+\]', '', text)
    text = re.sub(r'\[[\d\s,–\-—]+\]', '', text)

    # 15. Markdown Links and Standalone URLs
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'\[\s*\]\([^)]*\)', '', text)
    text = re.sub(r'https?://\S+', '', text)

    # 16. Inline Code (`code`)
    def repl_inline_code(m):
        code = m.group(1).strip()
        code = code.replace('_', ' ')
        code = code.replace('/', ' slash ')
        code = code.replace('.py', ' python file')
        code = code.replace('.ipynb', ' notebook')
        code = code.replace('.fits', ' fits file')
        return code
    text = re.sub(r'`([^`\n]+)`', repl_inline_code, text)

    # 17. Blockquotes and Horizontal Rules
    text = re.sub(r'^[ \t]*[-*_]{3,}[ \t]*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[ \t]*>+[ \t]*', '', text, flags=re.MULTILINE)

    # 18. Headers: Ensure punctuation at the end of headers
    def handle_header(m):
        header_text = m.group(2).strip()
        if not header_text:
            return ''
        if header_text[-1] not in '.!?:':
            header_text += '.'
        return f"\n\n{header_text}\n\n"

    text = re.sub(r'^(#{1,6})[ \t]+(.+)$', handle_header, text, flags=re.MULTILINE)

    # 19. Bullet and Numbered Lists
    def handle_numbered_item(m):
        num = m.group(1)
        content = m.group(2).strip()
        if content and content[-1] not in '.!?:':
            content += '.'
        return f"\n\n{num}. {content}\n\n"

    text = re.sub(r'^[ \t]*(\d+)\.[ \t]+(.+)$', handle_numbered_item, text, flags=re.MULTILINE)

    def handle_bullet(m):
        content = m.group(1).strip()
        if content and content[-1] not in '.!?:':
            content += '.'
        return f"\n{content}\n"

    text = re.sub(r'^[ \t]*[*+-][ \t]+(.+)$', handle_bullet, text, flags=re.MULTILINE)

    # Metadata lines (e.g. **Paper:** ... \n **Section:** ...)
    text = re.sub(r'(\*\*[A-Za-z0-9\s_-]+:\*\*.*?)\s{2,}\n', r'\1.\n\n', text)

    # 20. Inline styles: bold, italics, strikethrough
    text = re.sub(r'~~(.*?)~~', r'\1', text)
    text = re.sub(r'\*\*\*(.*?)\*\*\*', r'\1', text)
    text = re.sub(r'___(.*?)___', r'\1', text)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'__(.*?)__', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'_(.*?)_', r'\1', text)
    text = text.replace('*', '')

    # 21. Emojis and graphical icons
    text = remove_emojis(text)

    # 22. Punctuation & Whitespace cleanup
    text = text.replace('“', '"').replace('”', '"')
    text = text.replace('‘', "'").replace('’', "'")
    text = text.replace('—', ' - ').replace('–', ' - ')

    # Remove quotes around entire lines if present
    text = re.sub(r'^[ \t]*["\']+(.+?)["\']+[ \t]*$', r'\1', text, flags=re.MULTILINE)

    # Deduplicate repeated phrases in parentheses (e.g., "missing transverse energy (missing transverse energy)")
    text = re.sub(r'\b([A-Za-z\s]{4,})\s*\(\1\)', r'\1', text, flags=re.IGNORECASE)

    # Fix punctuation glitches
    text = re.sub(r':\s*\.', '.', text)
    text = re.sub(r':\s*:', ':', text)
    text = re.sub(r'\.{2,}', '.', text)
    text = re.sub(r'\(\s*\)', '', text)
    text = re.sub(r'\[\s*\]', '', text)
    text = re.sub(r'[ \t]+([.,!?:;])', r'\1', text)
    text = re.sub(r'  +', ' ', text)

    # 23. Paragraph spacing and sentence-boundary chunking
    def _split_long_para(para: str, max_chars: int = 400) -> List[str]:
        if len(para) <= max_chars:
            return [para]
        sentences = re.split(r'(?<=[.!?])\s+', para)
        chunks = []
        cur = []
        cur_len = 0
        for s in sentences:
            s_len = len(s)
            if cur and (cur_len + s_len > max_chars):
                chunks.append(" ".join(cur))
                cur = [s]
                cur_len = s_len
            else:
                cur.append(s)
                cur_len += s_len
        if cur:
            chunks.append(" ".join(cur))
        return chunks

    raw_paragraphs = text.split('\n')
    cleaned_paragraphs = []
    current_para = []

    for line in raw_paragraphs:
        stripped = line.strip()
        if stripped:
            current_para.append(stripped)
        else:
            if current_para:
                para_text = ' '.join(current_para)
                para_text = re.sub(r'\s+', ' ', para_text).strip()
                if para_text:
                    cleaned_paragraphs.extend(_split_long_para(para_text))
                current_para = []

    if current_para:
        para_text = ' '.join(current_para)
        para_text = re.sub(r'\s+', ' ', para_text).strip()
        if para_text:
            cleaned_paragraphs.extend(_split_long_para(para_text))

    cleaned_text = '\n\n'.join(cleaned_paragraphs)
    return cleaned_text

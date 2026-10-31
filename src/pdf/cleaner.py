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


def find_balanced_braces(s: str, start_pos: int):
    """Find matching closing brace for the brace starting at start_pos."""
    if start_pos >= len(s) or s[start_pos] != '{':
        return None, start_pos
    depth = 0
    for i in range(start_pos, len(s)):
        if s[i] == '{':
            depth += 1
        elif s[i] == '}':
            depth -= 1
            if depth == 0:
                return s[start_pos + 1:i], i + 1
    return None, start_pos


def replace_fractions(text: str, bengali: bool = False) -> str:
    """
    Replace LaTeX \\frac{num}{den} with (num over den) or (num/den),
    supporting arbitrarily nested curly braces and nested fractions.
    """
    idx = 0
    res = []
    while idx < len(text):
        frac_pos = text.find(r'\frac', idx)
        if frac_pos == -1:
            res.append(text[idx:])
            break
        res.append(text[idx:frac_pos])
        curr = frac_pos + 5
        while curr < len(text) and text[curr].isspace():
            curr += 1
        num, next_pos = find_balanced_braces(text, curr)
        if num is not None:
            curr = next_pos
            while curr < len(text) and text[curr].isspace():
                curr += 1
            den, end_pos = find_balanced_braces(text, curr)
            if den is not None:
                num_cleaned = replace_fractions(num, bengali)
                den_cleaned = replace_fractions(den, bengali)
                if bengali:
                    res.append(f"({num_cleaned}/{den_cleaned})")
                else:
                    res.append(f"({num_cleaned} over {den_cleaned})")
                idx = end_pos
                continue
        # Fallback for single-token fraction, e.g. \frac 1 2
        m_single = re.match(r'\\frac\s*\{?([a-zA-Z0-9]+)\}?\s*\{?([a-zA-Z0-9]+)\}?', text[frac_pos:])
        if m_single:
            if bengali:
                res.append(f"({m_single.group(1)}/{m_single.group(2)})")
            else:
                res.append(f"({m_single.group(1)} over {m_single.group(2)})")
            idx = frac_pos + m_single.end()
        else:
            res.append(text[frac_pos:frac_pos + 5])
            idx = frac_pos + 5
    return "".join(res)


def unwrap_font_wrappers(text: str) -> str:
    """
    Unwrap LaTeX font and text wrappers like \\text{...}, \\mathbf{...}, \\mathrm{...},
    supporting nested wrappers.
    """
    macros = ["text", "mathrm", "mathbf", "mathcal", "operatorname", "mathit", "boldsymbol", "bm", "rm", "textbf", "textit"]
    changed = True
    while changed:
        changed = False
        for macro in macros:
            pattern = "\\" + macro
            idx = 0
            res = []
            while idx < len(text):
                pos = text.find(pattern, idx)
                if pos == -1:
                    res.append(text[idx:])
                    break
                after = pos + len(pattern)
                if after < len(text) and text[after].isalpha():
                    res.append(text[idx:after])
                    idx = after
                    continue
                res.append(text[idx:pos])
                curr = after
                while curr < len(text) and text[curr].isspace():
                    curr += 1
                inner, end_pos = find_balanced_braces(text, curr)
                if inner is not None:
                    res.append(" " + inner + " ")
                    idx = end_pos
                    changed = True
                else:
                    res.append(text[pos:after])
                    idx = after
            text = "".join(res)
    return text


def clean_math_to_spoken(expr: str) -> str:
    """
    Convert mathematical / scientific expressions into spoken plain English.
    """
    s = expr.strip()
    if s.startswith('$$') and s.endswith('$$'):
        s = s[2:-2].strip()
    elif s.startswith('$') and s.endswith('$'):
        s = s[1:-1].strip()

    # Unwrap font wrappers first so nested wrappers like \mathbf{...\text{...}} are handled
    s = unwrap_font_wrappers(s)

    # 1. Degrees, arcseconds, arcminutes, percent
    # Degrees
    s = re.sub(r'1\s*\^\\circ\b|1\s*\^\{\\circ\}', '1 degree', s)
    s = re.sub(r'(\d+(?:\.\d+)?)\s*\^\\circ\b|(\d+(?:\.\d+)?)\s*\^\{\\circ\}', r'\1 degrees', s)
    s = re.sub(r'\^\\circ\b|\^\{\\circ\}|\\circ\b', ' degrees', s)

    # Arcseconds / Arcminutes
    s = re.sub(r"1\s*''|1\s*\"|1\s*\\prime\\prime(?![a-zA-Z])", '1 arcsecond', s)
    s = re.sub(r"(\d+(?:\.\d+)?)\s*''|(\d+(?:\.\d+)?)\s*\"|(\d+(?:\.\d+)?)\s*\\prime\\prime(?![a-zA-Z])", r'\1 arcseconds', s)
    s = re.sub(r"1\s*'|1\s*\\prime(?![a-zA-Z])", '1 arcminute', s)
    s = re.sub(r"(\d+(?:\.\d+)?)\s*'|(\d+(?:\.\d+)?)\s*\\prime(?![a-zA-Z])", r'\1 arcminutes', s)
    s = re.sub(r"^\s*''\s*$|^\s*\"\s*$", 'arcseconds', s)
    s = re.sub(r"^\s*'\s*$", 'arcminutes', s)

    # Per units
    s = re.sub(r'/\s*(?:\\text\{pixel\}|pixel)\b', ' per pixel', s)
    s = re.sub(r'/\s*(?:\\text\{arcsec\}|arcsec)\b', ' per arcsecond', s)
    s = re.sub(r'\\text\{km\}/\\text\{s\}|km/s\b', ' kilometers per second', s)
    s = re.sub(r'\\text\{m\}/\\text\{s\}|m/s\b', ' meters per second', s)

    # Percent
    s = re.sub(r'(\d+(?:\.\d+)?)\s*\\%', r'\1 percent', s)
    s = re.sub(r'\\%', ' percent', s)

    # Astrophysics units (Megaparsecs, kiloparsecs, parsecs, etc.)
    s = re.sub(r'\b1\s*(?:\\text\{Mpc\}|Mpc)\b', '1 Megaparsec', s)
    s = re.sub(r'(\d+(?:\.\d+)?)\s*(?:\\text\{Mpc\}|Mpc)\b', r'\1 Megaparsecs', s)
    s = re.sub(r'\\text\{Mpc\}|\bMpc\b', 'Megaparsecs', s)
    s = re.sub(r'\b1\s*(?:\\text\{kpc\}|kpc)\b', '1 kiloparsec', s)
    s = re.sub(r'(\d+(?:\.\d+)?)\s*(?:\\text\{kpc\}|kpc)\b', r'\1 kiloparsecs', s)
    s = re.sub(r'\\text\{kpc\}|\bkpc\b', 'kiloparsecs', s)
    s = re.sub(r'\b1\s*(?:\\text\{pc\}|pc)\b', '1 parsec', s)
    s = re.sub(r'(\d+(?:\.\d+)?)\s*(?:\\text\{pc\}|pc)\b', r'\1 parsecs', s)
    s = re.sub(r'\\text\{pc\}|\bpc\b', 'parsecs', s)
    s = re.sub(r'\\text\{rad\}|\brad\b', ' radians', s)
    s = re.sub(r'\\text\{arcsec\}|\barcsec\b', ' arcseconds', s)
    s = re.sub(r'\\text\{arcmin\}|\barcmin\b', ' arcminutes', s)
    s = re.sub(r'\b1\s*(?:solar masses|solar mass)\b', '1 solar mass', s)
    s = re.sub(r'M_\\odot\b|M_\{\\odot\}|\\text\{M\}_\{\\odot\}|Msun\b', ' solar masses ', s)
    s = re.sub(r'\\odot', ' sun ', s)

    # Specific units, astrophysics and chemistry constants
    s = re.sub(r'1\\,\s*\\text\{rad\}\s*\\approx\s*206,?265\'\'', '1 radian is approximately 206,265 arcseconds', s)
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

    # 3. Fractions (using balanced braces to support arbitrary nested braces)
    s = replace_fractions(s, bengali=False)

    # 4. Calculus (Limits, Integrals, Sums, Partials)
    s = re.sub(r'\\lim_\{([^{}]+)\\to\s*([^{}]+)\}', r'the limit as \1 approaches \2 of ', s)
    s = re.sub(r'\\int_\{([^}]+)\}\^\{([^}]+)\}', r'the integral from \1 to \2 of ', s)
    s = re.sub(r'\\int', 'the integral of ', s)
    s = re.sub(r'\\sum_\{([^}]+)\}\^\{([^}]+)\}', r'the sum from \1 to \2 of ', s)
    s = re.sub(r'\\sum', 'the sum of ', s)
    s = re.sub(r'\\frac\{\\partial\s*([A-Za-z])\}\{\\partial\s*([A-Za-z])\}', r'partial \1 over partial \2', s)

    # 5. Roots
    for _ in range(3):
        if r'\sqrt' not in s:
            break
        s = re.sub(r'\\sqrt\[([^\]]+)\]\{([^{}]+)\}', r'the \1 root of \2', s)
        s = re.sub(r'\\sqrt\{([^{}]+)\}', r'the square root of (\1)', s)

    # 6. Parentheses and Braces Delimiters
    s = re.sub(r'\\left\(|\\right\)', ' ', s)
    s = re.sub(r'\\left\[|\\right\]', ' ', s)
    s = re.sub(r'\\left\\\{|\\right\\\}', ' ', s)
    s = re.sub(r'\\left\||\\right\|', ' ', s)

    # 7. Math Operators and Relations
    s = re.sub(r'\\equiv\b', ' is defined as ', s)
    s = re.sub(r'\\xrightarrow\[(.*?)\]\{(.*?)\}', r' \2 ', s)
    s = re.sub(r'\\xrightarrow\{(.*?)\}', ' maps to ', s)

    for pat, rep in MATH_OPERATORS:
        s = re.sub(pat, rep, s)
    for pat, rep in MATH_RELATIONS:
        s = re.sub(pat, rep, s)

    # 8. Greek Letters (use (?![a-zA-Z]) so subscripts like \theta_E match)
    for greek, spoken in GREEK_LETTERS.items():
        s = re.sub(r'\\' + greek + r'(?![a-zA-Z])', f' {spoken} ', s)

    # 9. Vector and Accent Decorators
    s = re.sub(r'\\vec\{([^}]+)\}', r'\1 vector', s)
    s = re.sub(r'\\hat\{([^}]+)\}', r'\1 hat', s)
    s = re.sub(r'\\bar\{([^}]+)\}', r'\1 bar', s)
    s = re.sub(r'\\tilde\{([^}]+)\}', r'\1 tilde', s)
    s = re.sub(r'\\dot\{([^}]+)\}', r'\1 dot', s)

    # 10. Powers and Exponents
    s = re.sub(r'10\^\{-(\d+)\}|10\^-(\d+)', r'10 to the minus \1\2', s)
    s = re.sub(r'10\^\{(\d+)\}|10\^(\d+)', r'10 to the \1\2', s)
    s = re.sub(r'r\^\{-1\}|r\^-1', 'r to the minus 1', s)
    s = re.sub(r'r\^0', 'r to the power of 0', s)
    s = re.sub(r'\^2\b|\^\{2\}', ' squared ', s)
    s = re.sub(r'\^3\b|\^\{3\}', ' cubed ', s)
    s = re.sub(r'\^\{([^{}]+)\}', r' to the power of \1 ', s)
    s = re.sub(r'\^([0-9a-zA-Z])', r' to the power of \1 ', s)

    # 11. Subscripts
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

    # 12. Clean remaining LaTeX markers
    s = re.sub(r'\\[a-zA-Z]+', ' ', s)
    s = re.sub(r'[{}]', '', s)
    s = s.replace('=', ' equals ')
    s = s.replace('+', ' plus ')
    s = s.replace('-', ' minus ')
    s = s.replace(r'\,', ' ')
    s = s.replace('&', ' and ')
    s = s.replace('|', ' ')
    s = re.sub(r'\s*<\s*', ' is less than ', s)
    s = re.sub(r'\s*>\s*', ' is greater than ', s)

    # 13. Expand standalone units attached to numbers
    s = re.sub(r'(\b\d+(?:\.\d+)?\s*)eV\b', r'\1 electron volts', s)
    s = re.sub(r'(\b\d+(?:\.\d+)?\s*)m\b', r'\1 meters', s)
    s = re.sub(r'(\b\d+(?:\.\d+)?\s*)cm\b', r'\1 centimeters', s)
    s = re.sub(r'(\b\d+(?:\.\d+)?\s*)km\b', r'\1 kilometers', s)
    s = re.sub(r'(\b\d+(?:\.\d+)?\s*)s\b', r'\1 seconds', s)

    # Clean stray quotes
    s = re.sub(r"['\"]+", '', s)

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


DIAGRAM_LANGUAGES = {
    'mermaid', 'plantuml', 'uml', 'dot', 'graphviz',
    'flowchart', 'diagram', 'tikz', 'wavedrom', 'd2', 'nomnoml'
}


def clean_markdown_for_tts(
    markdown_text: str,
    remove_display_equations: bool = True,
    drop_code: bool = False,
    drop_diagrams: bool = False,
    strip_inline_math: bool = False,
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

    # 2. Strip AI agent / tool execution logs
    # e.g. "Ran list files in workspace", "Analyzed README.md:L1-24", "Ran ... · Exited with code 127"
    text = re.sub(
        r'^[ \t]*(?:Ran\s+.*|Analyzed\s+.*(?::L\d+.*)?|Viewed\s+.*|Inspected\s+.*|Checked\s+.*|Read\s+.*)(?:\s*·\s*Exited with code\s+\d+)?$\n?',
        '',
        text,
        flags=re.MULTILINE
    )

    # 3. Strip HTML comments, control characters, and replacement chars
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
    text = re.sub(r'[\ufffd\x00-\x08\x0b\x0c\x0e-\x1f\x7f]+', '', text)

    # 4. Strip HTML media elements (<svg>, <video>, <audio>)
    text = re.sub(r'<svg\b[^>]*>.*?</svg>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<video\b[^>]*>.*?</video>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<audio\b[^>]*>.*?</audio>', '', text, flags=re.DOTALL | re.IGNORECASE)

    # 5. Handle HTML <summary>, <details>, <progress>, <meter>
    text = re.sub(r'<summary\b[^>]*>(.*?)</summary>', r'\n\1\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</?details\b[^>]*>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<progress[^>]*value="([^"]+)"[^>]*>.*?</progress>', r'\1 percent', text, flags=re.IGNORECASE)
    text = re.sub(r'<meter[^>]*value="([^"]+)"[^>]*>(.*?)</meter>', r'\2', text, flags=re.IGNORECASE)

    # 6. Nested image links and standalone images
    text = re.sub(r'\[!\[.*?\]\(.*?\)\]\(.*?\)', '', text)
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)

    # 7. Escaped currency expressions (e.g. \$100, \$5.50)
    text = re.sub(r'\\\$(\d+)\.(\d{2})\b', r'\1 dollars and \2 cents', text)
    text = re.sub(r'\\\$(\d+)\b', r'\1 dollars', text)

    # 8. Unescaped currency NOT enclosed in math
    # Currency with range (e.g. $10 to $20, $10 and $20)
    text = re.sub(r'(?<![\$\w])\$(\d+(?:\.\d{2})?)\b(?=\s+(?:and|or|to|-|—)\s+\$\d+)', r'\1 dollars', text)
    # Currency at end or followed by punctuation/non-math words without matching closing $
    text = re.sub(r'(?<![\$\w])\$(\d+)\.(\d{2})\b(?![^$\n]*\$)', r'\1 dollars and \2 cents', text)
    text = re.sub(r'(?<![\$\w])\$(\d+)\b(?![^$\n]*\$)', r'\1 dollars', text)

    # 9. Handle Display Math ($$...$$ and \[...\]) BEFORE inline math
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

    # 10. Handle Inline Math ($...$ and \(...\))
    def handle_inline_math(m):
        if strip_inline_math:
            return ""
        inner = m.group(1)
        spoken = clean_math_to_spoken(inner)
        return f" {spoken} " if spoken else ""

    text = re.sub(r'(?<!\$)\$(?!\$)([^\$\n]+?)(?<!\$)\$(?!\$)', handle_inline_math, text)
    text = re.sub(r'\\\(([^)]+)\\\)', handle_inline_math, text)

    # Any remaining unclosed currency or stray dollar signs
    text = re.sub(r'(?<![\$\w])\$(\d+)\.(\d{2})\b', r'\1 dollars and \2 cents', text)
    text = re.sub(r'(?<![\$\w])\$(\d+)\b', r'\1 dollars', text)
    text = text.replace('$', '')

    # 11. Handle Code Blocks and Diagrams (``` and ~~~)
    def handle_code_block(m):
        lang = (m.group(1) or "").strip().lower()
        code_content = m.group(2) or ""
        if lang in DIAGRAM_LANGUAGES or is_ascii_diagram(code_content):
            if drop_diagrams:
                return ""
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

    # 12. Convert Markdown Tables into spoken sentences
    table_pattern = re.compile(r'(?:^[ \t]*\|.*\|[ \t]*$\n?)+', re.MULTILINE)
    text = table_pattern.sub(lambda m: convert_markdown_table_to_sentences(m.group(0)), text)

    # 13. GitHub-style Alert Callouts (> [!NOTE], > [!WARNING], etc.)
    text = re.sub(r'^\s*>\s*\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]', r'\1:', text, flags=re.MULTILINE | re.IGNORECASE)

    # 14. Checklists / Tasks
    text = re.sub(r'^\s*[-*]\s*\[x\]\s*', 'Completed: ', text, flags=re.MULTILINE | re.IGNORECASE)
    text = re.sub(r'^\s*[-*]\s*\[\s*\]\s*', 'Task: ', text, flags=re.MULTILINE)

    # 15. Strip remaining HTML tags and decode HTML entities
    text = re.sub(r'</?[a-zA-Z][a-zA-Z0-9]*(?:\s+[^>]*)?/?>', ' ', text)
    text = html.unescape(text)

    # 16. Academic Citations & Footnotes
    text = re.sub(r'\(\s*(?:e\.g\.|see)\s*\[[\d\s,–\-—]+\]\s*\)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^\s*\[\^[0-9]+\]:\s*', 'Footnote: ', text, flags=re.MULTILINE)
    text = re.sub(r'\[\^[0-9]+\]', '', text)
    text = re.sub(r'\[[\d\s,–\-—]+\]', '', text)

    # 17. Markdown Links and Standalone URLs
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'\[\s*\]\([^)]*\)', '', text)
    text = re.sub(r'https?://\S+', '', text)

    # 18. Inline Code (`code`)
    def repl_inline_code(m):
        code = m.group(1).strip()
        code = code.replace('_', ' ')
        code = code.replace('/', ' slash ')
        code = code.replace('.py', ' python file')
        code = code.replace('.ipynb', ' notebook')
        code = code.replace('.fits', ' fits file')
        return code
    text = re.sub(r'`([^`\n]+)`', repl_inline_code, text)

    # 19. Blockquotes and Horizontal Rules
    text = re.sub(r'^[ \t]*[-*_]{3,}[ \t]*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[ \t]*>+[ \t]*', '', text, flags=re.MULTILINE)

    # 20. Headers: Ensure punctuation at the end of headers
    def handle_header(m):
        header_text = m.group(2).strip()
        if not header_text:
            return ''
        if header_text[-1] not in '.!?:':
            header_text += '.'
        return f"\n\n{header_text}\n\n"

    text = re.sub(r'^(#{1,6})[ \t]+(.+)$', handle_header, text, flags=re.MULTILINE)

    # 21. Bullet and Numbered Lists
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

    # 22. Inline styles: bold, italics, strikethrough (respecting word boundaries)
    text = re.sub(r'~~(.*?)~~', r'\1', text)
    text = re.sub(r'\*\*\*(.*?)\*\*\*', r'\1', text)
    text = re.sub(r'___(.*?)___', r'\1', text)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'(?<!\w)__(?!\s)(.+?)(?<!\s)__(?!\w)', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'(?<!\w)_(?!\s)(.+?)(?<!\s)_(?!\w)', r'\1', text)
    text = text.replace('*', '')

    # Convert remaining underscores in filename-like or code-like patterns to spaces
    text = re.sub(r'(\w)_(\w)', r'\1 \2', text)

    # 23. Emojis and graphical icons
    text = remove_emojis(text)

    # 24. Punctuation & Whitespace cleanup
    text = text.replace('“', '"').replace('”', '"')
    text = text.replace('‘', "'").replace('’', "'")
    text = text.replace('—', ' - ').replace('–', ' - ')

    # Remove quotes around entire lines if present
    text = re.sub(r'^[ \t]*["\']+(.+?)["\']+[ \t]*$', r'\1', text, flags=re.MULTILINE)

    # Deduplicate repeated phrases in parentheses (e.g. "arcseconds (arcseconds)", "arcminutes (arcminutes)")
    text = re.sub(r'\b([A-Za-z\s]{3,})\s*\(\s*\1\s*\)', r'\1', text, flags=re.IGNORECASE)

    # Fix spaces inside parentheses and brackets
    text = re.sub(r'\(\s+', '(', text)
    text = re.sub(r'\s+\)', ')', text)
    text = re.sub(r'\[\s+', '[', text)
    text = re.sub(r'\s+\]', ']', text)

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

    def _flush_para(lines: List[str]):
        if not lines:
            return
        raw_block = '\n'.join(lines)
        if is_ascii_diagram(raw_block):
            if not drop_diagrams and diagram_placeholder:
                cleaned_paragraphs.append(diagram_placeholder)
            return
        para_text = ' '.join(lines)
        para_text = re.sub(r'\s+', ' ', para_text).strip()
        if para_text:
            cleaned_paragraphs.extend(_split_long_para(para_text))

    for line in raw_paragraphs:
        stripped = line.strip()
        if stripped:
            current_para.append(stripped)
        else:
            if current_para:
                _flush_para(current_para)
                current_para = []

    if current_para:
        _flush_para(current_para)

    cleaned_text = '\n\n'.join(cleaned_paragraphs)
    return cleaned_text


# ---------------------------------------------------------------------------
# Bengali Markdown & Math Cleaning Functions
# ---------------------------------------------------------------------------

def is_bengali_text(text: str) -> bool:
    """
    Detect if text contains significant Bengali characters.
    """
    bengali_chars = len(re.findall(r'[\u0980-\u09ff]', text))
    return bengali_chars > 20


def clean_bengali_math_plain(expr: str, strip_all: bool = False) -> str:
    """
    Clean or unwrap a LaTeX math expression for Bengali narration into clean plain notation,
    without inserting English spoken phrases.
    """
    if strip_all:
        return ""

    s = expr.strip()
    if s.startswith('$$') and s.endswith('$$'):
        s = s[2:-2].strip()
    elif s.startswith('$') and s.endswith('$'):
        s = s[1:-1].strip()

    # Check if expression ends in a scalar value after calculus, e.g. = 2
    m_calc = re.search(r'=\s*([0-9a-zA-Z/]+)\s*$', s)
    if m_calc and any(k in s for k in [r'\int', r'\cos', r'\sin', r'\sec', r'\tan']):
        return m_calc.group(1)

    # 1. Un-nest text wrappers with balanced braces
    s = unwrap_font_wrappers(s)
    s = re.sub(r'\\rm(?![a-zA-Z])', '', s)

    # 2. Astrophysics and physics symbols
    s = re.sub(r'\\odot', 'sun', s)
    s = re.sub(r"1''\.(\d+)", r"1.\1", s)
    s = re.sub(r"(\d+)''", r"\1 arcsec", s)
    s = re.sub(r'\\theta_\{?E\}?', 'theta_E', s)
    s = re.sub(r'\\Sigma_\{?(?:\\rm\s*)?cr\}?', 'Sigma_cr', s)
    s = re.sub(r'\\Delta\s*t', 'Delta t', s)
    s = re.sub(r'\\Delta(?![a-zA-Z])', 'Delta', s)
    s = re.sub(r'\\nabla_\\perp|\\nabla.*\\perp', 'nabla_perp', s)
    s = re.sub(r'\\nabla(?![a-zA-Z])', 'nabla', s)
    s = re.sub(r'\\partial(?![a-zA-Z])', 'd', s)

    # 3. Vector and accent decorators
    s = re.sub(r'\\(?:vec|hat|bar|tilde|dot)\{([^}]+)\}', r'\1', s)

    # 4. Standard trig / calculus functions
    s = re.sub(r'\\(sin|cos|tan|sec|csc|cot|log|ln|exp)(?![a-zA-Z])', r'\1 ', s)

    # 5. Fractions (using balanced braces)
    s = replace_fractions(s, bengali=True)

    # 6. Math relations
    s = re.sub(r'\\ll(?![a-zA-Z])', '<<', s)
    s = re.sub(r'\\gg(?![a-zA-Z])', '>>', s)
    s = re.sub(r'\\leq(?![a-zA-Z])|\\le(?![a-zA-Z])', '<=', s)
    s = re.sub(r'\\geq(?![a-zA-Z])|\\ge(?![a-zA-Z])', '>=', s)
    s = re.sub(r'\\neq(?![a-zA-Z])|\\ne(?![a-zA-Z])', '!=', s)
    s = re.sub(r'\\approx(?![a-zA-Z])|\\simeq(?![a-zA-Z])|\\sim(?![a-zA-Z])', '≈', s)
    s = re.sub(r'\\times(?![a-zA-Z])', '×', s)
    s = re.sub(r'\\cdot(?![a-zA-Z])', '·', s)
    s = re.sub(r'\\pm(?![a-zA-Z])', '±', s)
    s = re.sub(r'\\infty(?![a-zA-Z])', 'infinity', s)

    # 7. Greek letters (support subscripts like \theta_E)
    for grk, rep in GREEK_LETTERS.items():
        s = re.sub(r'\\' + grk + r'(?![a-zA-Z])', rep, s)

    # 8. Roots
    for _ in range(3):
        if r'\sqrt' not in s:
            break
        s = re.sub(r'\\sqrt\[([^\]]+)\]\{([^{}]+)\}', r'root(\1, \2)', s)
        s = re.sub(r'\\sqrt\{([^{}]+)\}', r'sqrt(\1)', s)

    # 9. Clean delimiters & braces
    s = re.sub(r'\\left\(|\\right\)', '', s)
    s = re.sub(r'\\left\[|\\right\]', '', s)
    s = re.sub(r'\\left\||\\right\|', '|', s)
    s = re.sub(r'\\left\\\{|\\right\\\}', '', s)
    s = re.sub(r'\\[,;! ]', ' ', s)

    # 10. Clean subscripts & superscripts
    s = re.sub(r'_\{([^}]+)\}', r'_\1', s)
    s = re.sub(r'\^\{([^}]+)\}', r'^\1', s)

    # Remove remaining backslashes and braces
    s = re.sub(r'\\[a-zA-Z]+', '', s)
    s = s.replace('{', '').replace('}', '')
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def clean_bengali_markdown(
    markdown_text: str,
    strip_math: bool = False,
) -> str:
    """
    Clean Bengali markdown or text for reading / TTS:
    - Normalizes line endings, strips YAML frontmatter, HTML tags, and comments
    - Removes LaTeX display equations and cleanly converts/simplifies inline math
    - Converts markdown tables into natural Bengali spoken sentences
    - Strips code blocks, diagrams, and emojis
    - Normalizes Bengali punctuation (Dari '।') and spacing
    - Paces paragraphs with Dari-aware sentence chunking
    """
    text = markdown_text.replace('\r\n', '\n').replace('\r', '\n')

    # 1. Strip YAML frontmatter
    text = re.sub(r'^---\s*\n.*?\n---\s*\n', '', text, flags=re.DOTALL)

    # 2. Strip AI agent / tool execution logs
    text = re.sub(
        r'^[ \t]*(?:Ran\s+.*|Analyzed\s+.*(?::L\d+.*)?|Viewed\s+.*|Inspected\s+.*|Checked\s+.*|Read\s+.*)(?:\s*·\s*Exited with code\s+\d+)?$\n?',
        '',
        text,
        flags=re.MULTILINE
    )

    # 3. Strip HTML comments, control chars, media
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
    text = re.sub(r'[\ufffd\x00-\x08\x0b\x0c\x0e-\x1f\x7f]+', '', text)
    text = re.sub(r'<(?:svg|video|audio|progress|meter)\b[^>]*>.*?</(?:svg|video|audio|progress|meter)>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'</?(?:details|summary)\b[^>]*>', '', text, flags=re.IGNORECASE)

    # 3. Strip images
    text = re.sub(r'\[!\[.*?\]\(.*?\)\]\(.*?\)', '', text)
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)

    # 4. Remove display equations ($$...$$ and \[...\])
    # If display math follows a colon at the end of a line, change the colon to a Bengali Dari '।'
    text = re.sub(r':[ \t]*\n[ \t]*\$\$[\s\S]*?\$\$', '।\n\n', text)
    text = re.sub(r'\$\$[\s\S]*?\$\$', '\n\n', text)
    text = re.sub(r':[ \t]*\n[ \t]*\\\[[\s\S]*?\\\]', '।\n\n', text)
    text = re.sub(r'\\\[[\s\S]*?\\\]', '\n\n', text)

    # 5. Clean inline LaTeX math ($...$ and \(...\)) BEFORE tables
    def _repl_inline(m):
        raw = m.group(1)
        cleaned = clean_bengali_math_plain(raw, strip_all=strip_math)
        return f" {cleaned} " if cleaned else ""

    text = re.sub(r'(?<!\$)\$(?!\$)([^\$\n]+?)(?<!\$)\$(?!\$)', _repl_inline, text)
    text = re.sub(r'\\\(([^)]+)\\\)', _repl_inline, text)
    text = text.replace('$', '')

    # 6. Remove code blocks and diagrams
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'~~~[\s\S]*?~~~', '', text)

    # 7. Convert Markdown Tables into spoken Bengali sentences
    def convert_bengali_table(table_block: str) -> str:
        lines = [line.strip() for line in table_block.strip().split('\n') if line.strip()]
        if len(lines) < 2:
            return ""
        sep_idx = -1
        for i, line in enumerate(lines):
            if re.match(r'^\|?(\s*:?-+:?\s*\|)+\s*:?-+:?\s*\|?$', line):
                sep_idx = i
                break
        data_rows = lines[sep_idx + 1:] if sep_idx != -1 else lines
        spoken_rows = []
        for row in data_rows:
            r = row.strip()
            if r.startswith('|'):
                r = r[1:]
            if r.endswith('|'):
                r = r[:-1]
            cols = [c.strip() for c in re.split(r'\s+\|\s+', r) if c.strip()]
            if not cols:
                continue
            first = cols[0]
            cleaned_cols = []
            for c in cols[1:]:
                c_clean = c.rstrip('.। ')
                if c_clean:
                    cleaned_cols.append(c_clean)
            if cleaned_cols:
                body = '। '.join(cleaned_cols)
                spoken_rows.append(f"{first}: {body}।")
            else:
                spoken_rows.append(f"{first}।")
        return '\n\n'.join(spoken_rows)

    table_pattern = re.compile(r'(?:^[ \t]*\|.*\|[ \t]*$\n?)+', re.MULTILINE)
    text = table_pattern.sub(lambda m: convert_bengali_table(m.group(0)), text)

    # 8. GitHub callouts
    text = re.sub(r'^\s*>\s*\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]', r'\1:', text, flags=re.MULTILINE | re.IGNORECASE)

    # 9. Strip HTML tags
    text = re.sub(r'</?[a-zA-Z][a-zA-Z0-9]*(?:\s+[^>]*)?/?>', ' ', text)

    # 10. Links and URLs
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'https?://\S+', '', text)

    # 11. Inline code (`code`)
    text = re.sub(r'`([^`\n]+)`', r'\1', text)

    # 12. Blockquotes and horizontal rules
    text = re.sub(r'^[ \t]*[-*_]{3,}[ \t]*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[ \t]*>+[ \t]*', '', text, flags=re.MULTILINE)

    # 13. Headers: strip '#' and ensure Bengali Dari '।' or ':' at end
    def handle_bengali_header(m):
        h = m.group(2).strip()
        if not h:
            return ''
        if h[-1] not in '।!?:.':
            h += '।'
        elif h[-1] == '.':
            h = h[:-1] + '।'
        return f"\n\n{h}\n\n"

    text = re.sub(r'^(#{1,6})[ \t]+(.+)$', handle_bengali_header, text, flags=re.MULTILINE)

    # 14. Numbered and bullet list items
    def handle_bengali_numbered(m):
        num = m.group(1)
        content = m.group(2).strip()
        if content and content[-1] not in '।!?:.':
            content += '।'
        elif content and content[-1] == '.':
            content = content[:-1] + '।'
        return f"\n\n{num}. {content}\n\n"

    text = re.sub(r'^[ \t]*(\d+|[০-৯]+)\.[ \t]+(.+)$', handle_bengali_numbered, text, flags=re.MULTILINE)

    def handle_bengali_bullet(m):
        content = m.group(1).strip()
        if content and content[-1] not in '।!?:.':
            content += '।'
        elif content and content[-1] == '.':
            content = content[:-1] + '।'
        return f"\n- {content}\n"

    text = re.sub(r'^[ \t]*[*+-][ \t]+(.+)$', handle_bengali_bullet, text, flags=re.MULTILINE)

    # 15. Bold, italics, strikethrough
    text = re.sub(r'~~(.*?)~~', r'\1', text)
    text = re.sub(r'\*\*\*(.*?)\*\*\*', r'\1', text)
    text = re.sub(r'___(.*?)___', r'\1', text)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'(?<!\w)__(?!\s)(.+?)(?<!\s)__(?!\w)', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'(?<!\w)_(?!\s)(.+?)(?<!\s)_(?!\w)', r'\1', text)
    text = text.replace('*', '')

    # 16. Emojis and symbols
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001F900-\U0001F9FF"
        "\U0001FA00-\U0001FA6F"
        "\U0001FA70-\U0001FAFF"
        "\U00002600-\U000026FF"
        "\U00002300-\U000023FF"
        "\U00002B00-\U00002BFF"
        "]+",
        flags=re.UNICODE
    )
    text = emoji_pattern.sub('', text)

    # 17. Clean punctuation glitches
    text = re.sub(r':\s*।', '।', text)
    text = re.sub(r'।\s*\.', '।', text)
    text = re.sub(r'\.\s*।', '।', text)
    text = re.sub(r'।{2,}', '।', text)
    # Fix spaces inside parentheses: '( x )' -> '(x)'
    text = re.sub(r'\(\s+', '(', text)
    text = re.sub(r'\s+\)', ')', text)
    # Fix spaces around hyphens in Bengali suffix: e.g. 'Phi -এ' -> 'Phi-এ', 'b -কে' -> 'b-কে'
    text = re.sub(r'([a-zA-Z0-9_]+)\s*-\s*([এওয়েরকেতে])', r'\1-\2', text)
    # Fix empty parentheses
    text = re.sub(r'\(\s*[:,-]?\s*\)', '', text)
    text = re.sub(r'\[\s*[:,-]?\s*\]', '', text)
    # Clean spaces before punctuation
    text = re.sub(r'[ \t]+([।,!?:;])', r'\1', text)
    text = re.sub(r'  +', ' ', text)

    # 18. Paragraph pacing with sentence-boundary chunking
    def _split_bengali_para(para: str, max_chars: int = 500):
        if len(para) <= max_chars:
            return [para]
        sentences = re.split(r'(?<!\b\d)(?<!\b[০-৯])(?<=[।!?])\s+', para)
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
                    cleaned_paragraphs.extend(_split_bengali_para(para_text))
                current_para = []

    if current_para:
        para_text = ' '.join(current_para)
        para_text = re.sub(r'\s+', ' ', para_text).strip()
        if para_text:
            cleaned_paragraphs.extend(_split_bengali_para(para_text))

    return '\n\n'.join(cleaned_paragraphs)


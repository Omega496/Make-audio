"""
Markdown cleaning module for Text-to-Speech (TTS).

Converts markdown documents (including academic notes, LaTeX formulas,
tables, ASCII art, citations, and markdown formatting) into natural,
fluent plain English suitable for TTS narration.
"""

import re
import unicodedata
from typing import Optional


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
        
        # Operators, comparisons, arrows
        (r'\\approx', ' approximately '),
        (r'\\sim|~', ' approximately '),
        (r'\\simeq', ' approximately '),
        (r'\\propto', ' proportional to '),
        (r'\\times', ' times '),
        (r'\\pm', ' plus or minus '),
        (r'\\mp', ' minus or plus '),
        (r'\\leq|\\le', ' less than or equal to '),
        (r'\\geq|\\ge', ' greater than or equal to '),
        (r'\\ll', ' much less than '),
        (r'\\gg', ' much greater than '),
        (r'\\neq', ' not equal to '),
        (r'\\longleftrightarrow', ' in equilibrium with '),
        (r'\\to|\\rightarrow', ' to '),
        (r'\\leftarrow', ' from '),
        
        # Mathematical < and > in formulas
        (r'\s*<\s*', ' less than '),
        (r'\s*>\s*', ' greater than '),
        (r'\s*=\s*', ' equals '),
        
        # Powers and exponents
        (r'10\^\{-(\d+)\}|10\^-(\d+)', r'10 to the minus \1\2'),
        (r'10\^\{(\d+)\}|10\^(\d+)', r'10 to the \1\2'),
        (r'r\^\{-1\}|r\^-1', 'r to the minus 1'),
        (r'r\^0', 'r to the power of 0'),
        (r'h\^2', 'h squared'),
        (r'c\^2', 'c squared'),
        (r'\^2', ' squared'),
        (r'\^3', ' cubed'),
        
        # Fractions
        (r'\\frac\{([^{}]+)\}\{([^{}]+)\}', r'\1 over \2'),
    ]
    
    for pattern, repl in replacements:
        s = re.sub(pattern, repl, s)
        
    # Greek letters
    greek_letters = {
        r'\\alpha': 'alpha', r'\\beta': 'beta', r'\\gamma': 'gamma', r'\\delta': 'delta',
        r'\\epsilon': 'epsilon', r'\\zeta': 'zeta', r'\\eta': 'eta', r'\\theta': 'theta',
        r'\\iota': 'iota', r'\\kappa': 'kappa', r'\\lambda': 'lambda', r'\\mu': 'mu',
        r'\\nu': 'nu', r'\\xi': 'xi', r'\\pi': 'pi', r'\\rho': 'rho',
        r'\\sigma': 'sigma', r'\\tau': 'tau', r'\\upsilon': 'upsilon', r'\\phi': 'phi',
        r'\\chi': 'chi', r'\\psi': 'psi', r'\\omega': 'omega',
        r'\\Gamma': 'Gamma', r'\\Delta': 'Delta', r'\\Theta': 'Theta', r'\\Lambda': 'Lambda',
        r'\\Xi': 'Xi', r'\\Pi': 'Pi', r'\\Sigma': 'Sigma', r'\\Upsilon': 'Upsilon',
        r'\\Phi': 'Phi', r'\\Psi': 'Psi', r'\\Omega': 'Omega'
    }
    for code, name in greek_letters.items():
        s = re.sub(code + r'\b', name, s)
        
    # Remove text wrappers like \text{...}, \mathrm{...}, \mathbf{...}
    s = re.sub(r'\\[a-zA-Z]+\{([^}]*)\}', r'\1', s)
    
    # Strip any remaining backslashed commands
    s = re.sub(r'\\[a-zA-Z]+', ' ', s)
    
    # Clean up subscripts and braces
    s = re.sub(r'_\{([^}]+)\}', r' \1', s)
    s = re.sub(r'_([a-zA-Z0-9]+)', r' \1', s)
    s = re.sub(r'_', ' ', s)
    s = re.sub(r'[{}]', '', s)
    
    # Expand units attached to numbers
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


def clean_markdown_for_tts(markdown_text: str, remove_display_equations: bool = True) -> str:
    """
    Clean markdown text for TTS narration:
    - Removes YAML frontmatter
    - Strips or converts LaTeX math to plain English
    - Removes citations ([1], [1-5], (e.g. [6]))
    - Converts tables to natural spoken sentences
    - Strips ASCII diagrams in code blocks
    - Strips markdown formatting (headers, blockquotes, bullets, links, bold/italics)
    - Deduplicates repeated phrases in parentheses
    - Normalizes punctuation and whitespace
    """
    text = markdown_text

    # 1. Strip YAML frontmatter if present
    text = re.sub(r'^---\s*\n.*?\n---\s*\n', '', text, flags=re.DOTALL)

    # 2. Strip HTML comments and explicit HTML tags (never match single < or > used in math)
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
    text = re.sub(r'</?[a-zA-Z][a-zA-Z0-9]*(?:\s+[^>]*)?/?>', ' ', text)

    # 3. Handle Display Math ($$...$$ and \[...\])
    if remove_display_equations:
        # If display math follows a colon at the end of a sentence, change the colon to a period
        text = re.sub(r':[ \t]*\n[ \t]*\$\$[\s\S]*?\$\$', '.\n\n', text)
        text = re.sub(r'\$\$[\s\S]*?\$\$', '\n\n', text)
        text = re.sub(r':[ \t]*\n[ \t]*\\\[[\s\S]*?\\\]', '.\n\n', text)
        text = re.sub(r'\\\[[\s\S]*?\\\]', '\n\n', text)
    else:
        def _spoken_display_math(m):
            return '\n\n' + clean_math_to_spoken(m.group(1)) + '.\n\n'
        text = re.sub(r'\$\$([\s\S]*?)\$\$', _spoken_display_math, text)
        text = re.sub(r'\\\[([\s\S]*?)\\\]', _spoken_display_math, text)

    # 4. Handle Code Blocks
    def handle_code_block(m):
        code_content = m.group(1)
        if is_ascii_diagram(code_content):
            return '\n\n'
        clean_lines = [l.strip() for l in code_content.splitlines() if l.strip()]
        if len(clean_lines) <= 5 and not any(ch in code_content for ch in "{}()<>=;"):
            return '\n\n' + '. '.join(clean_lines) + '.\n\n'
        return '\n\n'

    text = re.sub(r'```(?:[a-zA-Z0-9_-]*\n)?([\s\S]*?)```', handle_code_block, text)

    # 5. Convert Markdown Tables into spoken sentences
    table_pattern = re.compile(r'(?:^[ \t]*\|.*\|[ \t]*$\n?)+', re.MULTILINE)
    text = table_pattern.sub(lambda m: convert_markdown_table_to_sentences(m.group(0)), text)

    # 6. Convert Inline Math ($...$ and \(...\))
    def handle_inline_math(m):
        inner = m.group(1)
        return clean_math_to_spoken(inner)

    text = re.sub(r'\$([^$\n]+)\$', handle_inline_math, text)
    text = re.sub(r'\\\(([^)]+)\\\)', handle_inline_math, text)

    # 7. Strip Academic Citations
    text = re.sub(r'\(\s*(?:e\.g\.|see)\s*\[[\d\s,–\-—]+\]\s*\)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\[[\d\s,–\-—]+\]', '', text)

    # 8. Markdown Links and Images
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'https?://\S+', '', text)

    # 9. Blockquotes and Horizontal Rules
    text = re.sub(r'^[ \t]*[-*_]{3,}[ \t]*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[ \t]*>[ \t]*', '', text, flags=re.MULTILINE)

    # 10. Headers: Ensure punctuation at the end of headers
    def handle_header(m):
        header_text = m.group(2).strip()
        if not header_text:
            return ''
        if not header_text[-1] in '.!?:':
            header_text += '.'
        return f"\n\n{header_text}\n\n"

    text = re.sub(r'^(#{1,6})[ \t]+(.+)$', handle_header, text, flags=re.MULTILINE)

    # 11. Bullet and Numbered Lists
    # Numbered list items: keep on their own line
    def handle_numbered_item(m):
        num = m.group(1)
        content = m.group(2).strip()
        if content and content[-1] not in '.!?:':
            content += '.'
        return f"\n\n{num}. {content}\n\n"

    text = re.sub(r'^[ \t]*(\d+)\.[ \t]+(.+)$', handle_numbered_item, text, flags=re.MULTILINE)

    # Unordered bullets
    def handle_bullet(m):
        content = m.group(1).strip()
        if content and content[-1] not in '.!?:':
            content += '.'
        return f"\n{content}\n"

    text = re.sub(r'^[ \t]*[*+-][ \t]+(.+)$', handle_bullet, text, flags=re.MULTILINE)

    # Metadata lines (e.g. **Paper:** ... \n **Section:** ...)
    text = re.sub(r'(\*\*[A-Za-z0-9\s_-]+:\*\*.*?)\s{2,}\n', r'\1.\n\n', text)

    # 12. Inline styles: bold, italics, strikethrough, inline code
    text = re.sub(r'\*\*\*(.*?)\*\*\*', r'\1', text)
    text = re.sub(r'___(.*?)___', r'\1', text)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'__(.*?)__', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'_(.*?)_', r'\1', text)
    text = re.sub(r'~~(.*?)~~', r'\1', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)

    # 13. Emojis and graphical icons
    text = remove_emojis(text)

    # 14. Punctuation & Whitespace cleanup
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

    # Clean up paragraph spacing and chunk long blocks
    def _split_long_para(para: str, max_chars: int = 400) -> list:
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

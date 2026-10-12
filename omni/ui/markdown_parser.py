import re
import html
import markdown
from Foundation import NSData, NSDictionary
from AppKit import (
    NSAttributedString,
    NSHTMLTextDocumentType,
    NSDocumentTypeDocumentAttribute,
    NSCharacterEncodingDocumentAttribute,
    NSUTF8StringEncoding
)

SUPERSCRIPTS = {
    '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
    '+': '⁺', '-': '⁻', '=': '⁼', '(': '⁽', ')': '⁾', 'n': 'ⁿ', 'i': 'ⁱ', 'x': 'ˣ', 'y': 'ʸ', 'k': 'ᵏ'
}

SUBSCRIPTS = {
    '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄', '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉',
    '+': '₊', '-': '₋', '=': '₌', '(': '₍', ')': '₎', 'a': 'ₐ', 'e': 'ₑ', 'x': 'ₓ', 'y': 'ᵧ', 'i': 'ᵢ', 'n': 'ₙ'
}

def clean_latex_math(text: str) -> str:
    """Converts LaTeX math expressions into clean readable unicode typography."""
    
    # 1. Outer macros first: fractions
    # Repeat to handle nested fractions if any
    for _ in range(3):
        text = re.sub(r'\\frac\{([^{}]+)\}\{([^{}]+)\}', r'(\1 / \2)', text)

    # 2. Roots
    text = re.sub(r'\\sqrt\[([^\]]+)\]\{([^{}]+)\}', r'^{\1}√(\2)', text)
    text = re.sub(r'\\sqrt\{([^{}]+)\}', r'√(\1)', text)

    # 3. Operators & symbols
    symbols = [
        (r'\\pm', '±'),
        (r'\\mp', '∓'),
        (r'\\times', '×'),
        (r'\\div', '÷'),
        (r'\\cdot', '·'),
        (r'\\circ', '°'),
        (r'\\approx', '≈'),
        (r'\\neq?', '≠'),
        (r'\\leq?', '≤'),
        (r'\\geq?', '≥'),
        (r'\\infty', '∞'),
        (r'\\partial', '∂'),
        (r'\\nabla', '∇'),
        (r'\\int', '∫'),
        (r'\\sum', '∑'),
        (r'\\prod', '∏'),
        (r'\\in', '∈'),
        (r'\\notin', '∉'),
        (r'\\subset', '⊂'),
        (r'\\cup', '∪'),
        (r'\\cap', '∩'),
        (r'\\to|\\rightarrow', '→'),
        (r'\\leftarrow', '←'),
        (r'\\Rightarrow', '⇒'),
        (r'\\Leftrightarrow', '⇔'),
        (r'\\forall', '∀'),
        (r'\\exists', '∃'),
        (r'\\pi', 'π'),
        (r'\\alpha', 'α'),
        (r'\\beta', 'β'),
        (r'\\gamma', 'γ'),
        (r'\\theta', 'θ'),
        (r'\\lambda', 'λ'),
        (r'\\mu', 'μ'),
        (r'\\sigma', 'σ'),
        (r'\\omega', 'ω'),
        (r'\\Delta', 'Δ'),
        (r'\\Omega', 'Ω'),
        (r'\\text\{([^{}]+)\}', r'\1'),
        (r'\\mathbf\{([^{}]+)\}', r'\1'),
        (r'\\mathrm\{([^{}]+)\}', r'\1'),
        (r'\\mathit\{([^{}]+)\}', r'\1'),
    ]
    for pattern, repl in symbols:
        text = re.sub(pattern, repl, text)

    # 4. Superscripts & subscripts
    def format_sup(m):
        return "".join(SUPERSCRIPTS.get(c, c) for c in m.group(1))

    def format_sub(m):
        return "".join(SUBSCRIPTS.get(c, c) for c in m.group(1))

    text = re.sub(r'\^\{([0-9a-zA-Z+-=()]+)\}', format_sup, text)
    text = re.sub(r'\^([0-9a-zA-Z+-])', lambda m: SUPERSCRIPTS.get(m.group(1), '^' + m.group(1)), text)

    text = re.sub(r'\_\{([0-9a-zA-Z+-=()]+)\}', format_sub, text)
    text = re.sub(r'\_([0-9a-zA-Z+-])', lambda m: SUBSCRIPTS.get(m.group(1), '_' + m.group(1)), text)

    return text

def preprocess_markdown(md_text: str) -> str:
    """Preprocesses LaTeX blocks inside markdown before HTML conversion."""
    
    # Process display math blocks: $$...$$
    def replace_display_math(match):
        raw_eq = match.group(1).strip()
        cleaned = clean_latex_math(raw_eq)
        return f'\n<div class="math-block">{html.escape(cleaned)}</div>\n'

    md_text = re.sub(r'\$\$([\s\S]*?)\$\$', replace_display_math, md_text)

    # Process inline math: $...$ (avoiding currency $50)
    def replace_inline_math(match):
        raw_eq = match.group(1).strip()
        cleaned = clean_latex_math(raw_eq)
        return f'<span class="math-inline">{html.escape(cleaned)}</span>'

    md_text = re.sub(r'(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)', replace_inline_math, md_text)
    return md_text

DARK_CSS = """
<style>
body {
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", Arial, sans-serif;
    font-size: 14.5px;
    line-height: 1.55;
    color: #F0F2F5;
    background-color: transparent;
    margin: 0;
    padding: 4px;
}
h1, h2, h3, h4 {
    color: #61AFEF;
    font-weight: 600;
    margin-top: 14px;
    margin-bottom: 6px;
}
h1 { font-size: 18px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 4px; }
h2 { font-size: 16px; color: #98C379; }
h3 { font-size: 15px; color: #E5C07B; }
p {
    margin-top: 4px;
    margin-bottom: 8px;
}
strong, b {
    color: #FFFFFF;
    font-weight: 650;
}
ul, ol {
    margin-top: 4px;
    margin-bottom: 8px;
    padding-left: 20px;
}
li {
    margin-bottom: 4px;
}
code {
    font-family: "SF Mono", Menlo, Monaco, "Courier New", monospace;
    font-size: 13px;
    background-color: rgba(255, 255, 255, 0.1);
    color: #E5C07B;
    padding: 2px 5px;
    border-radius: 4px;
}
pre {
    background-color: #1A1D24;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 8px;
    padding: 10px 12px;
    margin: 10px 0;
    overflow-x: auto;
}
pre code {
    background-color: transparent;
    padding: 0;
    color: #98C379;
    font-size: 13px;
    line-height: 1.45;
}
.math-block {
    background-color: rgba(97, 175, 239, 0.08);
    border-left: 3px solid #61AFEF;
    border-radius: 4px;
    padding: 8px 12px;
    margin: 8px 0;
    font-family: "SF Mono", Menlo, Monaco, monospace;
    font-size: 14px;
    color: #61AFEF;
    letter-spacing: 0.3px;
}
.math-inline {
    font-family: "SF Mono", Menlo, Monaco, monospace;
    color: #61AFEF;
    background-color: rgba(97, 175, 239, 0.12);
    padding: 1px 4px;
    border-radius: 3px;
    font-size: 13.5px;
}
hr {
    border: none;
    border-top: 1px solid rgba(255, 255, 255, 0.12);
    margin: 12px 0;
}
</style>
"""

def markdown_to_attributed_string(raw_text: str) -> NSAttributedString:
    """Converts markdown text to a styled macOS NSAttributedString using user CSS."""
    processed_md = preprocess_markdown(raw_text)
    
    html_body = markdown.markdown(
        processed_md,
        extensions=['fenced_code', 'tables', 'nl2br']
    )
    
    from omni.config import Config
    custom_css = Config.load_css()
    css_block = f"<style>{custom_css}</style>" if custom_css else DARK_CSS
    
    full_html = f"<html><head>{css_block}</head><body>{html_body}</body></html>"
    html_bytes = full_html.encode('utf-8')
    
    data = NSData.dataWithBytes_length_(html_bytes, len(html_bytes))
    options = {
        NSDocumentTypeDocumentAttribute: NSHTMLTextDocumentType,
        NSCharacterEncodingDocumentAttribute: NSUTF8StringEncoding
    }
    
    attr_str, _, err = NSAttributedString.alloc().initWithData_options_documentAttributes_error_(
        data, options, None, None
    )
    
    if attr_str:
        return attr_str
    
    # Fallback to plain string
    return NSAttributedString.alloc().initWithString_(raw_text)

#!/usr/bin/env python3
"""
Prep Books 2 and 3 for audiobook production.
Split into sections, optimize for Voxtral prosody.
"""
import re
import os
import sys


def optimize_for_voxtral(text):
    """Apply all prosody optimizations."""
    # Remove markdown
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'\1', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'(?<!\w)\*([^*]+?)\*(?!\w)', r'\1', text)
    text = re.sub(r'\\_', '', text)
    text = re.sub(r'_{3,}', '', text)
    text = re.sub(r'^\|.*\|$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^### ', '', text, flags=re.MULTILINE)
    text = re.sub(r'^#### ', '', text, flags=re.MULTILINE)
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
    text = text.replace('\\newpage', '')

    # Remove parentheticals
    text = re.sub(r'\(Henkel\)', '', text)
    text = re.sub(r'\(Quad\)', '', text)
    text = text.replace('gener8tor accelerator', 'startup accelerator')
    text = re.sub(r'Inc\.\s*', '', text)

    # Figure/table references
    text = re.sub(r'\[VISUAL:.*?\]', '', text)
    text = re.sub(r'See Figure \d+\.\d+[^.]*\.', '', text)
    text = re.sub(r'\(see Figure \d+\.\d+[^)]*\)', '', text)
    text = re.sub(r'Figure \d+\.\d+ —[^\n]*\n', '', text)

    # Numbers & symbols
    text = re.sub(r'\$(\d+(?:\.\d+)?)\s*trillion', r'\1 trillion dollars', text)
    text = re.sub(r'\$(\d+(?:\.\d+)?)\s*billion', r'\1 billion dollars', text)
    text = re.sub(r'\$(\d+(?:\.\d+)?)\s*million', r'\1 million dollars', text)
    text = re.sub(r'\$(\d[\d,]*)', lambda m: m.group(1).replace(',', '') + ' dollars', text)
    text = re.sub(r'(\d+)%', r'\1 percent', text)

    # Abbreviations
    abbrevs = {
        'CFO': 'C.F.O.', 'CEO': 'C.E.O.', 'COO': 'C.O.O.',
        'CPA': 'C.P.A.', 'IPO': 'I.P.O.', 'ERP': 'E.R.P.',
        'CRM': 'C.R.M.', 'SWOT': 'S.W.O.T.', 'PESTLE': 'P.E.S.T.L.E.',
        'PESTEL': 'P.E.S.T.E.L.', 'EBITDA': 'E.B.I.T.D.A.',
        'ESG': 'E.S.G.', 'RACI': 'R.A.C.I.',
        'ROI': 'R.O.I.', 'KPI': 'K.P.I.', 'KPIs': 'K.P.I.s',
        'GDP': 'G.D.P.', 'AI': 'A.I.', 'LLM': 'L.L.M.',
        'API': 'A.P.I.', 'GPU': 'G.P.U.', 'EPA': 'E.P.A.',
        'NASA': 'NASA', 'NATO': 'NATO',  # keep these as words
        'P&L': 'P. and L.', 'R&D': 'R. and D.', 'M&A': 'M. and A.',
        'S&OP': 'S. and O.P.', 'SGA': 'S.G. and A.',
        'SaaS': 'Software as a Service',
        'RAG': 'R.A.G.', 'NLP': 'N.L.P.',
        'ERRC': 'E.R.R.C.', 'RBV': 'R.B.V.',
        'VRIN': 'V.R.I.N.',
    }
    for abbr, spoken in abbrevs.items():
        text = re.sub(r'\b' + re.escape(abbr) + r'\b', spoken, text)

    text = text.replace('e.g.', 'for example')
    text = text.replace('i.e.', 'that is')
    text = text.replace('etc.', 'and so on.')
    text = text.replace('vs.', 'versus')

    # Em-dashes to ellipses
    text = text.replace(' --- ', '... ')
    text = text.replace(' -- ', '... ')
    text = text.replace(' — ', '... ')
    text = text.replace('---', '... ')
    text = text.replace('—', '... ')
    text = text.replace('--', '... ')

    # Breathing room
    for phrase in ['However,', 'In other words,', 'For example,',
                   'The key ', 'The result ', 'The bottom line',
                   'In summary,', 'Ultimately,']:
        text = re.sub(r'(?<=[.!?])\s+(' + re.escape(phrase) + ')', r'\n\n\1', text)

    # Clean
    text = re.sub(r'\n{4,}', '\n\n\n', text)
    text = re.sub(r'  +', ' ', text)
    text = re.sub(r' \n', '\n', text)
    text = re.sub(r'\n ', '\n', text)

    return text.strip()


def split_and_optimize(manuscript_path, output_dir, book_name):
    """Split manuscript into sections and optimize each."""
    os.makedirs(output_dir, exist_ok=True)

    with open(manuscript_path, 'r') as f:
        text = f.read()

    # Remove before Dedication
    ded = re.search(r'^## Dedication', text, re.MULTILINE)
    if ded:
        text = text[ded.start():]

    # Remove TOC
    text = re.sub(r'## Table of Contents.*?(?=## Preface|## How to Use|\n# )', '', text, flags=re.DOTALL)

    # Remove back matter
    for marker in ['## About the Author', '## Other Books', '## Connect with Kenneth',
                   '## Sources and Further Reading', '## Sources and References',
                   '# Tools and Worksheets', '# Recommended Reading',
                   'The remaining pages']:
        idx = text.find(marker)
        if idx > 0 and idx > len(text) * 0.7:
            text = text[:idx]
            break

    # Split on ## headers (sections)
    parts = re.split(r'\n(#{1,2} [^\n]+)\n', text)

    sections = []
    idx = 0
    for i in range(len(parts)):
        part = parts[i].strip()
        if not part:
            continue

        if re.match(r'^#{1,2} ', part):
            title = part.lstrip('#').strip()
            body = parts[i + 1].strip() if i + 1 < len(parts) else ''
            if len(body.split()) < 10:
                continue

            content = f'{title}\n\n{body}'
            content = optimize_for_voxtral(content)

            slug = re.sub(r'[^a-z0-9]+', '_', title.lower())[:40]
            fname = f'{idx:02d}_{slug}.txt'

            with open(os.path.join(output_dir, fname), 'w') as f:
                f.write(content)

            wc = len(content.split())
            print(f'  {fname}: {wc} words')
            idx += 1

    print(f'\n  {idx} sections created in {output_dir}')
    return idx


if __name__ == '__main__':
    BASE = '/home/kmangum/constitution-federation/collaboration/threads/02_mangumcfo/books/kdp'

    print('=' * 60)
    print('BOOK 2: Harnessing Artificial Intelligence')
    print('=' * 60)
    split_and_optimize(
        f'{BASE}/02_harnessing_ai/v1.2/manuscript_v1.2.md',
        f'{BASE}/02_harnessing_ai/v1.2/audiobook/sections_optimized',
        'Harnessing AI'
    )

    print('\n' + '=' * 60)
    print('BOOK 3: Blueprint for Brilliance')
    print('=' * 60)
    split_and_optimize(
        f'{BASE}/03_blueprint/v1.1/manuscript_v1.1.md',
        f'{BASE}/03_blueprint/v1.1/audiobook/sections_optimized',
        'Blueprint for Brilliance'
    )

    print('\n' + '=' * 60)
    print('ALL BOOKS PREPPED')
    print('=' * 60)

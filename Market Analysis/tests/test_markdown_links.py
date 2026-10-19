"""
test_markdown_links.py
======================
Empirical verification test suite for markdown link resolution across:
- Market Analysis/00_Inditex_Stage1_IC_Overview.md
- Market Analysis/STAGE_1_EXECUTION_PLAN.md
- Market Analysis/modules/*.md

Tests:
- All relative markdown links [text](target) point to existing files on disk.
- All file:// URI links resolve to existing files on disk.
- Internal anchors (#heading) match existing headers within the document.
"""

from pathlib import Path
import re
import unittest
from urllib.parse import urlparse, unquote
from urllib.request import url2pathname
from typing import Dict, List, Tuple


class TestMarkdownLinks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).resolve().parent.parent.parent
        cls.market_analysis_dir = cls.project_root / 'Market Analysis'
        
        # Collect all markdown files in Market Analysis
        cls.md_files = sorted(list(cls.market_analysis_dir.glob('*.md')) + list((cls.market_analysis_dir / 'modules').glob('*.md')))

    def _extract_headings(self, text: str) -> List[str]:
        """Extract markdown headings and convert them to GitHub-style anchor slugs."""
        slugs = []
        for line in text.splitlines():
            line = line.strip()
            if line.startswith('#'):
                heading_text = line.lstrip('#').strip()
                heading_text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', heading_text)
                slug = heading_text.lower()
                slug = re.sub(r'[^\w\s-]', '', slug)
                slug = re.sub(r'[\s]+', '-', slug).strip('-')
                slugs.append(slug)
        return slugs

    def _extract_links(self, text: str) -> List[Tuple[str, str, int]]:
        """
        Extract all markdown links: returns (link_text, link_target, line_number).
        Ignores code blocks (``` ... ```).
        """
        links = []
        in_code_block = False
        lines = text.splitlines()

        for line_num, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith('```'):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue

            matches = re.findall(r'!?\[([^\]]*)\]\(([^)]+)\)', line)
            for text_match, target_match in matches:
                target_clean = target_match.strip()
                # Split at whitespace in case of title attribute
                target_clean = target_clean.split()[0].strip('"').strip("'")
                links.append((text_match, target_clean, line_num))

        return links

    def test_relative_and_file_links_resolve_to_existing_files(self):
        """Verify that every relative or file URI link resolves to an existing file on disk."""
        broken_links = []
        verified_count = 0

        for md_path in self.md_files:
            content = md_path.read_text(encoding='utf-8')
            links = self._extract_links(content)

            for text, target, line_num in links:
                # Skip external web protocols
                if target.startswith(('http://', 'https://', 'mailto:')):
                    continue
                # Skip pure anchor links
                if target.startswith('#'):
                    continue

                verified_count += 1

                # Handle file:// URIs
                if target.startswith('file://'):
                    parsed = urlparse(target)
                    path_str = unquote(parsed.path)
                    if path_str.startswith('/') and len(path_str) > 2 and path_str[2] == ':':
                        path_str = path_str[1:]
                    resolved_target = Path(path_str).resolve()
                else:
                    file_part = target.split('#')[0]
                    if not file_part:
                        continue
                    file_part = unquote(file_part)
                    resolved_target = (md_path.parent / file_part).resolve()

                if not resolved_target.exists():
                    broken_links.append({
                        'source_file': str(md_path.relative_to(self.project_root)),
                        'line': line_num,
                        'link_text': text,
                        'target': target,
                        'resolved_path': str(resolved_target)
                    })

        print(f"\n[TestMarkdownLinks] Verified {verified_count} file/relative links across {len(self.md_files)} markdown files.")
        if broken_links:
            msg = f"Found {len(broken_links)} broken file/relative links:\n"
            for b in broken_links:
                msg += f"  - {b['source_file']}:{b['line']} -> [{b['link_text']}]({b['target']}) (Resolved to: {b['resolved_path']})\n"
            self.fail(msg)

    def test_internal_anchors_validity(self):
        """Verify that internal page anchor links (#anchor) correspond to valid headings."""
        broken_anchors = []
        total_anchors = 0

        for md_path in self.md_files:
            content = md_path.read_text(encoding='utf-8')
            headings = self._extract_headings(content)
            links = self._extract_links(content)

            for text, target, line_num in links:
                if target.startswith('#') and len(target) > 1:
                    total_anchors += 1
                    anchor = target[1:].lower().replace('%20', '-')
                    if anchor not in headings:
                        matched = any(anchor in h or h in anchor for h in headings)
                        if not matched:
                            broken_anchors.append({
                                'source_file': str(md_path.relative_to(self.project_root)),
                                'line': line_num,
                                'anchor': target
                            })

        print(f"[TestMarkdownLinks] Verified {total_anchors} internal anchor links.")
        if broken_anchors:
            msg = f"Found {len(broken_anchors)} internal anchor references with no matching heading:\n"
            for b in broken_anchors:
                msg += f"  - {b['source_file']}:{b['line']} -> {b['anchor']}\n"
            self.fail(msg)


if __name__ == '__main__':
    unittest.main()

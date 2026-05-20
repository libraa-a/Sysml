"""Builtin DOCX generation helpers extracted from docgen."""

from __future__ import annotations

import html
import io
import zipfile


def split_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def markdown_to_docx_builtin(markdown: str) -> bytes:
    """Generate a simple DOCX without Pandoc/Quarto."""
    body_parts: list[str] = []
    table_rows: list[list[str]] = []

    def flush_table() -> None:
        nonlocal table_rows
        if table_rows:
            body_parts.append(_docx_table(table_rows))
        table_rows = []

    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line:
            flush_table()
            body_parts.append("<w:p/>")
            continue

        if line.startswith("|") and line.endswith("|"):
            cells = split_table_row(line)
            if set(line.replace("|", "").replace(":", "").replace(" ", "")) == {"-"}:
                continue
            table_rows.append(cells)
            continue

        flush_table()
        if line.startswith("# "):
            body_parts.append(_docx_paragraph(line[2:].strip(), "Heading1"))
        elif line.startswith("## "):
            body_parts.append(_docx_paragraph(line[3:].strip(), "Heading2"))
        elif line.startswith("### "):
            body_parts.append(_docx_paragraph(line[4:].strip(), "Heading3"))
        elif line.startswith("- "):
            body_parts.append(_docx_paragraph(f"* {line[2:].strip()}"))
        else:
            body_parts.append(_docx_paragraph(line.lstrip("#").strip()))

    flush_table()
    return _docx_package("\n".join(body_parts))


def _docx_package(document_body: str) -> bytes:
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>"""
    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""
    document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    {document_body}
    <w:sectPr>
      <w:pgSz w:w="11906" w:h="16838"/>
      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/>
    </w:sectPr>
  </w:body>
</w:document>"""
    styles_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
    <w:rPr><w:rFonts w:ascii="Segoe UI" w:hAnsi="Segoe UI" w:eastAsia="Microsoft YaHei"/><w:sz w:val="21"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading1">
    <w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/>
    <w:pPr><w:spacing w:before="240" w:after="160"/></w:pPr>
    <w:rPr><w:rFonts w:ascii="Segoe UI" w:hAnsi="Segoe UI" w:eastAsia="Microsoft YaHei"/><w:b/><w:sz w:val="32"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading2">
    <w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/>
    <w:pPr><w:spacing w:before="200" w:after="120"/></w:pPr>
    <w:rPr><w:rFonts w:ascii="Segoe UI" w:hAnsi="Segoe UI" w:eastAsia="Microsoft YaHei"/><w:b/><w:color w:val="0F766E"/><w:sz w:val="26"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading3">
    <w:name w:val="heading 3"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/>
    <w:rPr><w:rFonts w:ascii="Segoe UI" w:hAnsi="Segoe UI" w:eastAsia="Microsoft YaHei"/><w:b/><w:sz w:val="23"/></w:rPr>
  </w:style>
</w:styles>"""

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as docx:
        docx.writestr("[Content_Types].xml", content_types)
        docx.writestr("_rels/.rels", rels)
        docx.writestr("word/document.xml", document_xml)
        docx.writestr("word/styles.xml", styles_xml)
    return buffer.getvalue()


def _docx_paragraph(text: str, style: str | None = None) -> str:
    style_xml = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    return f"<w:p>{style_xml}<w:r><w:rPr>{_docx_run_fonts()}</w:rPr><w:t xml:space=\"preserve\">{html.escape(text)}</w:t></w:r></w:p>"


def _docx_table(rows: list[list[str]]) -> str:
    row_xml = []
    for row in rows:
        cells = "".join(
            f"<w:tc><w:tcPr><w:tcW w:w=\"2400\" w:type=\"dxa\"/></w:tcPr>{_docx_paragraph(cell)}</w:tc>"
            for cell in row
        )
        row_xml.append(f"<w:tr>{cells}</w:tr>")
    borders = """
      <w:tblBorders>
        <w:top w:val="single" w:sz="4" w:space="0" w:color="D8DEE8"/>
        <w:left w:val="single" w:sz="4" w:space="0" w:color="D8DEE8"/>
        <w:bottom w:val="single" w:sz="4" w:space="0" w:color="D8DEE8"/>
        <w:right w:val="single" w:sz="4" w:space="0" w:color="D8DEE8"/>
        <w:insideH w:val="single" w:sz="4" w:space="0" w:color="D8DEE8"/>
        <w:insideV w:val="single" w:sz="4" w:space="0" w:color="D8DEE8"/>
      </w:tblBorders>"""
    return f"<w:tbl><w:tblPr><w:tblW w:w=\"0\" w:type=\"auto\"/>{borders}</w:tblPr>{''.join(row_xml)}</w:tbl>"


def _docx_run_fonts() -> str:
    return '<w:rFonts w:ascii="Segoe UI" w:hAnsi="Segoe UI" w:eastAsia="Microsoft YaHei"/><w:sz w:val="21"/>'

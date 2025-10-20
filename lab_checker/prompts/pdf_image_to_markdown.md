# PDF Image to Markdown Conversion Prompt

Convert the PDF image to Markdown format. Follow these rules strictly:

## Text Content
- Extract all text exactly as shown
- Use Markdown formatting to preserve structure:
  - `# ` for headings
  - `**bold**` for emphasis
  - `*italic*` for italics
  - `-` for bullet points
  - `1.` for numbered lists
  - `` ` `` for inline code
  - ` ``` ` for code blocks
  - `|` for table formatting

## Diagrams and Visual Elements
Convert any diagrams, charts, or visual elements to Mermaid syntax:
- Flowcharts: Use `graph TD`
- Sequence diagrams: Use `sequenceDiagram`
- State diagrams: Use `stateDiagram`
- ER diagrams: Use `erDiagram`
- Gantt charts: Use `gantt`
- Class diagrams: Use `classDiagram`
- Tables and charts: Use text representation or Mermaid syntax

Wrap diagrams in code blocks:
```
\`\`\`mermaid
[diagram code]
\`\`\`
```

## Output Rules
- Output ONLY the extracted Markdown content
- Do NOT add commentary, explanations, or headers like "Here is the markdown:" 
- Do NOT add notes about what was found
- Preserve exact structure and hierarchy from the image
- No extra text before or after the Markdown content

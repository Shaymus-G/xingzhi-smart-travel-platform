/**
 * 轻量 Markdown → HTML 转换器
 *
 * 专为 AI 聊天消息设计，处理 DeepSeek 返回的格式化内容。
 * 覆盖：标题/段落/换行/嵌套列表/粗体/斜体/行内代码/代码块/链接/引用。
 *
 * 安全约束：
 *   - 先 HTML 转义原始内容，再还原安全标签
 *   - 链接限制 http/https/mailto 协议
 *   - 不执行 script、不渲染事件属性
 *
 * 不依赖第三方库，在 uni-app H5 和 App 运行时行为一致。
 */

// ==================== HTML 转义 ====================

const HTML_ESCAPE_MAP: Record<string, string> = {
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;',
}

function escapeHtml(text: string): string {
  return text.replace(/[&<>"']/g, (ch) => HTML_ESCAPE_MAP[ch] || ch)
}

// ==================== 安全链接 ====================

function safeLinkHref(url: string): string {
  const trimmed = url.trim()
  if (
    /^https?:\/\//i.test(trimmed) ||
    /^mailto:/i.test(trimmed) ||
    /^\//.test(trimmed) ||
    /^\.\.?\//.test(trimmed)
  ) {
    return trimmed
  }
  return ''
}

// ==================== 行内格式化 ====================

/**
 * 对已转义的文本应用行内 Markdown 规则
 *
 * 必须在块级结构（标题/列表项/段落）内部调用。
 * 代码块内容不应经过此函数。
 */
function applyInlineFormatting(escapedText: string): string {
  let result = escapedText

  // 行内代码 `code` — 必须在链接和粗体之前处理
  result = result.replace(
    /`([^`]+)`/g,
    (_m: string, code: string) => `<code>${code}</code>`,
  )

  // 图片 ![alt](url) — 仅保留 alt 文本
  result = result.replace(
    /!\[([^\]]*)\]\([^)]+\)/g,
    (_m: string, alt: string) => alt || '[图片]',
  )

  // 链接 [text](url)
  result = result.replace(
    /\[([^\]]+)\]\(([^)]+)\)/g,
    (_m: string, text: string, url: string) => {
      const href = safeLinkHref(url)
      if (!href) return text
      return `<a href="${href}" target="_blank" rel="noopener">${text}</a>`
    },
  )

  // 粗体 **text**
  result = result.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')

  // 斜体 *text*（避免匹配 ** 残余）
  result = result.replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, '<em>$1</em>')

  return result
}

// ==================== 列表类型 ====================

type ListType = 'ul' | 'ol'

/** 列表栈条目：记录当前打开的列表上下文 */
interface ListStackEntry {
  type: ListType
  indent: number
}

/** 缩进空格数计算：Tab 按 4 空格归一化 */
function computeIndent(spaces: string): number {
  let count = 0
  for (const ch of spaces) {
    count += ch === '\t' ? 4 : 1
  }
  return count
}

/** 判断是否为列表项行，返回匹配信息或 null */
function matchListItem(line: string): {
  indent: number
  marker: string
  listType: ListType
  content: string
} | null {
  // 匹配: 前导空格 + 标记 + 空格 + 内容
  // 标记: - * + 或 数字.
  const m = line.match(/^(\s*)([-*+]|\d+\.)\s+(.+)$/)
  if (!m) return null

  const indent = computeIndent(m[1])
  const marker = m[2]
  const listType: ListType = /^\d+\.$/.test(marker) ? 'ol' : 'ul'
  const content = m[3]

  return { indent, marker, listType, content }
}

/**
 * 处理一组连续列表行，生成嵌套 HTML
 *
 * 使用缩进栈算法：
 *   - 缩进增加 → 进入子列表（push 新上下文，子列表嵌套在父 <li> 内）
 *   - 缩进相同 → 同级新条目（关闭上一个 <li>，开新 <li>）
 *   - 缩进减少 → 弹出栈直到匹配层级
 *   - 列表结束 → 关闭所有 open 的 <li> 和列表标签
 *
 * 生成合法 HTML：
 *   <ul class="md-list md-list-level-1">
 *     <li>一级
 *       <ul class="md-list md-list-level-2">
 *         <li>二级</li>
 *       </ul>
 *     </li>
 *   </ul>
 */
function renderListBlock(listLines: string[]): string {
  const stack: ListStackEntry[] = []
  const parts: string[] = []

  for (let i = 0; i < listLines.length; i++) {
    const match = matchListItem(listLines[i])
    if (!match) continue

    const { indent, listType, content } = match

    // 找到应在的栈层级：最近的 indent < 当前 indent 的条目是父级
    while (stack.length > 0) {
      const top = stack[stack.length - 1]
      if (top.indent < indent) break
      // 缩进 <= 栈顶 → 关闭当前层级
      stack.pop()
      parts.push(`</li></${top.type}>`)
    }

    // 是否需要开新列表（栈为空 或 当前 indent > 栈顶 indent）
    const parentIndent = stack.length > 0 ? stack[stack.length - 1].indent : -1

    if (stack.length === 0 || indent > parentIndent) {
      // 开新列表（嵌套在父 <li> 内或顶层）
      const level = stack.length + 1
      parts.push(`<${listType} class="md-list md-list-level-${level}">`)
      stack.push({ type: listType, indent })
      parts.push(`<li>${applyInlineFormatting(content)}`)
    } else if (indent === parentIndent && stack.length > 0) {
      // 同级新条目
      // 检查列表类型是否一致 — 不一致时关闭旧列表开新列表
      const top = stack[stack.length - 1]
      if (top.type !== listType) {
        stack.pop()
        parts.push(`</li></${top.type}>`)
        const level = stack.length + 1
        parts.push(`<${listType} class="md-list md-list-level-${level}">`)
        stack.push({ type: listType, indent })
      } else {
        parts.push('</li>')
      }
      parts.push(`<li>${applyInlineFormatting(content)}`)
    } else {
      // 安全回退：视为同级
      parts.push('</li>')
      parts.push(`<li>${applyInlineFormatting(content)}`)
    }
  }

  // 关闭所有 open 的层级
  while (stack.length > 0) {
    const ctx = stack.pop()!
    parts.push(`</li></${ctx.type}>`)
  }

  return parts.join('')
}

// ==================== 表格类型与解析 ====================

type MarkdownTableAlignment = 'left' | 'center' | 'right'

interface MarkdownTableBlock {
  headers: string[]
  alignments: MarkdownTableAlignment[]
  rows: string[][]
}

/** 表格分隔行判定：每单元格至少 3 个 -，可前缀 : 或后缀 : 表示对齐 */
function isMarkdownTableSeparator(line: string): boolean {
  // 去除首尾可选管道和空白
  let content = line.trim()
  if (content.startsWith('|')) content = content.slice(1)
  if (content.endsWith('|')) content = content.slice(0, -1)

  const cells = content.split('|').map((c) => c.trim())
  if (cells.length === 0) return false

  return cells.every((cell) => /^:?-{3,}:?$/.test(cell))
}

/** 从分隔行提取对齐方式 */
function parseAlignments(line: string, colCount: number): MarkdownTableAlignment[] {
  let content = line.trim()
  if (content.startsWith('|')) content = content.slice(1)
  if (content.endsWith('|')) content = content.slice(0, -1)

  const cells = content.split('|').map((c) => c.trim())
  const alignments: MarkdownTableAlignment[] = []

  for (let i = 0; i < colCount; i++) {
    const cell = cells[i] || ''
    const left = cell.startsWith(':')
    const right = cell.endsWith(':')
    if (left && right) alignments.push('center')
    else if (right) alignments.push('right')
    else alignments.push('left')
  }

  return alignments
}

/**
 * 安全拆分表格行单元格
 *
 * 识别行内代码 `` ` `` 中的 `|`，不将其视为列分隔符。
 * 支持反斜杠转义 `\|`。
 * 去除可选的首尾 `|`。
 */
function splitMarkdownTableRow(line: string): string[] {
  let content = line.trim()

  // 去除可选的首尾管道符
  if (content.startsWith('|')) content = content.slice(1)
  if (content.endsWith('|')) content = content.slice(0, -1)

  const cells: string[] = []
  let current = ''
  let inCode = false

  for (let i = 0; i < content.length; i++) {
    const ch = content[i]

    if (ch === '`') {
      inCode = !inCode
      current += ch
    } else if (ch === '\\' && i + 1 < content.length && content[i + 1] === '|') {
      // 转义管道符：\| → |
      current += '|'
      i++ // skip the |
    } else if (ch === '|' && !inCode) {
      // 真正的列分隔符
      cells.push(current.trim())
      current = ''
    } else {
      current += ch
    }
  }

  cells.push(current.trim())
  return cells
}

/** 规范化表格行列数（以表头为准） */
function normalizeRowColumns(headers: string[], rowCells: string[]): string[] {
  const result = [...rowCells]

  // 少于表头 → 尾部补空
  while (result.length < headers.length) {
    result.push('')
  }

  // 多于表头 → 合并多余列到最后
  if (result.length > headers.length) {
    const extra = result.splice(headers.length - 1)
    result[headers.length - 1] = [result[headers.length - 1], ...extra]
      .filter((c) => c !== '')
      .join(' ')
  }

  return result
}

/** 尝试从 lines[startIndex] 开始解析表格，成功返回 { block, nextIndex } */
function parseMarkdownTable(
  lines: string[],
  startIndex: number,
): { block: MarkdownTableBlock; nextIndex: number } | null {
  if (startIndex + 1 >= lines.length) return null

  const headerLine = lines[startIndex]
  const separatorLine = lines[startIndex + 1].trim()

  // 表头行必须包含管道符，分隔行必须符合格式
  if (!headerLine.includes('|') || !isMarkdownTableSeparator(separatorLine)) {
    return null
  }

  const headers = splitMarkdownTableRow(headerLine)
  if (headers.length === 0) return null

  const alignments = parseAlignments(separatorLine, headers.length)
  // 补齐缺失的对齐信息
  while (alignments.length < headers.length) {
    alignments.push('left')
  }

  // 收集数据行
  const rows: string[][] = []
  let i = startIndex + 2

  while (i < lines.length) {
    const candidate = lines[i]
    if (!candidate.trim()) break // 空行结束表格
    if (candidate.trim().startsWith('%%CODEBLOCK_')) break
    if (!candidate.includes('|')) break // 不含管道符 → 不是表格行

    const rowCells = splitMarkdownTableRow(candidate)
    rows.push(normalizeRowColumns(headers, rowCells))
    i++
  }

  return { block: { headers, alignments, rows }, nextIndex: i }
}

/** 将表格块渲染为 HTML 字符串（H5 用） */
function renderMarkdownTable(block: MarkdownTableBlock): string {
  const parts: string[] = []

  parts.push('<div class="md-table-scroll"><table class="md-table">')

  // thead
  parts.push('<thead><tr>')
  for (let ci = 0; ci < block.headers.length; ci++) {
    const align = block.alignments[ci] || 'left'
    const cellContent = applyInlineFormatting(block.headers[ci])
    parts.push(`<th class="md-align-${align}">${cellContent}</th>`)
  }
  parts.push('</tr></thead>')

  // tbody
  parts.push('<tbody>')
  for (const row of block.rows) {
    parts.push('<tr>')
    for (let ci = 0; ci < block.headers.length; ci++) {
      const align = block.alignments[ci] || 'left'
      const cellContent = applyInlineFormatting(row[ci] || '')
      parts.push(`<td class="md-align-${align}">${cellContent}</td>`)
    }
    parts.push('</tr>')
  }
  parts.push('</tbody>')

  parts.push('</table></div>')
  return parts.join('')
}

// ==================== 块级输出类型 ====================

/** 渲染块：HTML 片段或结构化表格 */
export type MarkdownRenderBlock =
  | { type: 'html'; html: string }
  | { type: 'table'; headers: string[]; alignments: MarkdownTableAlignment[]; rows: string[][] }

// ==================== 公开 API ====================

/**
 * 将 AI 返回的 Markdown 文本转换为安全 HTML 字符串
 *
 * 处理流程：
 *   1. 代码块提取（```...``` → 占位符保护）
 *   2. HTML 转义
 *   3. 按行分类 & 块级分组
 *   4. 嵌套列表栈解析
 *   5. 标题 / 引用 / 段落处理
 *   6. 代码块还原
 *
 * @param markdown 原始 Markdown 文本
 * @returns 安全的 HTML 字符串，可用于 <rich-text> :nodes 属性
 */
export function markdownToHtml(markdown: string): string {
  if (!markdown) return ''

  // ===== 1. 提取代码块 =====
  const codeBlocks: string[] = []
  let text = markdown.replace(
    /```(\w*)\n([\s\S]*?)```/g,
    (_match: string, lang: string, code: string) => {
      const idx = codeBlocks.length
      const escapedCode = escapeHtml(code.trimEnd())
      const langAttr = lang ? ` data-lang="${escapeHtml(lang)}"` : ''
      codeBlocks.push(`<pre${langAttr}><code>${escapedCode}</code></pre>`)
      return `%%CODEBLOCK_${idx}%%`
    },
  )

  // ===== 2. HTML 转义 =====
  text = escapeHtml(text)

  // ===== 3. 按行处理：分类 + 块级分组 =====
  const lines = text.split('\n')
  const outputParts: string[] = []
  let i = 0

  while (i < lines.length) {
    const rawLine = lines[i]
    const trimmed = rawLine.trim()

    // 空白行 → 段落分隔
    if (!trimmed) {
      outputParts.push('<br>')
      i++
      continue
    }

    // 代码块占位符 → 直接保留
    if (trimmed.startsWith('%%CODEBLOCK_')) {
      outputParts.push(trimmed)
      i++
      continue
    }

    // 表格 — 必须在水平线之前检查（分隔行含 --- 但前后有管道符）
    if (trimmed.includes('|') && i + 1 < lines.length) {
      const tableResult = parseMarkdownTable(lines, i)
      if (tableResult) {
        outputParts.push(renderMarkdownTable(tableResult.block))
        i = tableResult.nextIndex
        continue
      }
    }

    // 水平线
    if (/^(---|\*\*\*|___)$/.test(trimmed)) {
      outputParts.push('<hr>')
      i++
      continue
    }

    // 标题
    const hMatch = trimmed.match(/^(#{1,3}) (.+)$/)
    if (hMatch) {
      const level = hMatch[1].length
      const hContent = applyInlineFormatting(hMatch[2])
      outputParts.push(`<h${level}>${hContent}</h${level}>`)
      i++
      continue
    }

    // 引用（连续引用行合并为一个 blockquote）
    if (trimmed.startsWith('&gt; ')) {
      const quoteLines: string[] = []
      while (i < lines.length && lines[i].trim().startsWith('&gt; ')) {
        quoteLines.push(lines[i].trim().slice(5)) // 去掉 "&gt; "
        i++
      }
      const quoteContent = quoteLines
        .map((ql) => `<p>${applyInlineFormatting(ql)}</p>`)
        .join('')
      outputParts.push(`<blockquote>${quoteContent}</blockquote>`)
      continue
    }

    // 列表项 — 收集连续列表行并整体处理
    if (matchListItem(rawLine)) {
      const listLines: string[] = []
      while (i < lines.length) {
        const candidate = lines[i]
        if (matchListItem(candidate)) {
          listLines.push(candidate)
          i++
        } else if (candidate.trim() === '') {
          // 空行结束列表
          break
        } else if (candidate.trim().startsWith('%%CODEBLOCK_')) {
          // 代码块占位符结束列表
          break
        } else {
          // 非列表非空行：可能是列表项的续行（后续说明文字）
          // 检查是否有缩进（至少 2 空格）
          if (/^ {2,}\S/.test(candidate)) {
            // 视为最后一条列表项的后续文本
            if (listLines.length > 0) {
              listLines[listLines.length - 1] += ' ' + candidate.trim()
            }
            i++
          } else {
            break
          }
        }
      }
      outputParts.push(renderListBlock(listLines))
      continue
    }

    // 普通段落行 — 连续非空非特殊行合并为一个段落
    const paraLines: string[] = []
    while (i < lines.length) {
      const pl = lines[i]
      if (!pl.trim() || pl.trim().startsWith('%%CODEBLOCK_')) break
      if (
        /^(#{1,3}) /.test(pl.trim()) ||
        pl.trim().startsWith('&gt; ') ||
        matchListItem(pl) ||
        /^(---|\*\*\*|___)$/.test(pl.trim()) ||
        (pl.includes('|') && isMarkdownTableSeparator(lines[i + 1]?.trim() || ''))
      ) {
        break
      }
      paraLines.push(pl.trim())
      i++
    }
    if (paraLines.length > 0) {
      const paraContent = applyInlineFormatting(paraLines.join(' '))
      outputParts.push(`<p>${paraContent}</p>`)
    }
  }

  // ===== 4. 组装 =====
  let html = outputParts.join('\n')

  // 压缩连续 <br>
  html = html.replace(/(<br>\n?){3,}/g, '<br><br>')

  // ===== 5. 还原代码块 =====
  html = html.replace(/%%CODEBLOCK_(\d+)%%/g, (_match: string, idx: string) => {
    return codeBlocks[parseInt(idx, 10)] || ''
  })

  return html
}

/**
 * 将 Markdown 文本转为 rich-text 组件可用的 HTML 字符串
 */
export function markdownToRichTextNodes(markdown: string): string {
  return markdownToHtml(markdown)
}

/**
 * 将 Markdown 文本解析为块级渲染结果数组
 *
 * 表格块从 HTML 中分离，由调用方使用原生组件渲染，
 * 解决 rich-text 在 App 端对 <table> 支持不完整的问题。
 *
 * @returns MarkdownRenderBlock[] — HTML 块和表格块交替
 */
export function markdownToBlocks(markdown: string): MarkdownRenderBlock[] {
  if (!markdown) return []

  // 先用完整 HTML 解析器生成 HTML
  const html = markdownToHtml(markdown)

  // 从 HTML 中提取表格占位块
  const blocks: MarkdownRenderBlock[] = []

  // 分离 <div class="md-table-scroll">...</div> 为独立表格块
  const TABLE_REGEX = /<div class="md-table-scroll"><table class="md-table">([\s\S]*?)<\/table><\/div>/g

  let lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = TABLE_REGEX.exec(html)) !== null) {
    // 表格之前的 HTML
    const before = html.slice(lastIndex, match.index).trim()
    if (before) {
      blocks.push({ type: 'html', html: before })
    }

    // 表格块 — 从 HTML 中提取数据
    const tableHtml = match[1]
    const tableBlock = extractTableFromHtml(tableHtml)
    if (tableBlock) {
      blocks.push({ type: 'table', ...tableBlock })
    } else {
      // 降级：作为 HTML 输出
      blocks.push({ type: 'html', html: match[0] })
    }

    lastIndex = match.index + match[0].length
  }

  // 尾部 HTML
  const after = html.slice(lastIndex).trim()
  if (after) {
    blocks.push({ type: 'html', html: after })
  }

  return blocks
}

/** 从渲染后的 HTML 片段反向提取表格数据（用于块级渲染） */
function extractTableFromHtml(
  tableInner: string,
): { headers: string[]; alignments: MarkdownTableAlignment[]; rows: string[][] } | null {
  // 解析 thead → headers + alignments
  const theadMatch = tableInner.match(/<thead>([\s\S]*?)<\/thead>/)
  const headers: string[] = []
  const alignments: MarkdownTableAlignment[] = []

  if (theadMatch) {
    const thRegex = /<th class="md-align-(left|center|right)">([\s\S]*?)<\/th>/g
    let thMatch: RegExpExecArray | null
    while ((thMatch = thRegex.exec(theadMatch[1])) !== null) {
      alignments.push(thMatch[1] as MarkdownTableAlignment)
      headers.push(thMatch[2])
    }
  }

  // 解析 tbody → rows
  const tbodyMatch = tableInner.match(/<tbody>([\s\S]*?)<\/tbody>/)
  const rows: string[][] = []

  if (tbodyMatch) {
    const trRegex = /<tr>([\s\S]*?)<\/tr>/g
    let trMatch: RegExpExecArray | null
    while ((trMatch = trRegex.exec(tbodyMatch[1])) !== null) {
      const tdRegex = /<td class="md-align-(?:left|center|right)">([\s\S]*?)<\/td>/g
      const row: string[] = []
      let tdMatch: RegExpExecArray | null
      while ((tdMatch = tdRegex.exec(trMatch[1])) !== null) {
        row.push(tdMatch[1])
      }
      rows.push(row)
    }
  }

  if (headers.length === 0) return null
  return { headers, alignments, rows }
}

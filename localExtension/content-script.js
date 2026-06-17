function isVisibleElement(el) {
  if (!(el instanceof HTMLElement)) return false
  const style = window.getComputedStyle(el)
  if (style.visibility === 'hidden' || style.display === 'none' || parseFloat(style.opacity) === 0) {
    return false
  }
  const rect = el.getBoundingClientRect()
  return rect.width > 0 && rect.height > 0
}

function getVisibleTextNodes(root = document.body) {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      if (!node.nodeValue || !node.nodeValue.trim()) return NodeFilter.FILTER_REJECT
      const parent = node.parentElement
      if (!parent || !isVisibleElement(parent)) return NodeFilter.FILTER_REJECT
      return NodeFilter.FILTER_ACCEPT
    },
  })

  const nodes = []
  let node = walker.nextNode()
  while (node) {
    nodes.push(node)
    node = walker.nextNode()
  }
  return nodes
}

function extractWords(text) {
  const tokens = text.match(/\b[A-Za-z][A-Za-z'’\-]{2,}\b/g) || []
  return tokens
    .map((token) => token.trim())
    .filter((token) => token.length >= 3)
}

function findVocabSection() {
  const labels = Array.from(document.querySelectorAll('body *')).filter((el) => {
    return el.textContent && /Từ\s+vựng\s+nên\s+học/i.test(el.textContent)
  })

  for (const label of labels) {
    let node = label
    for (let depth = 0; depth < 6 && node; depth += 1) {
      const vocabList = node.querySelector('ul')
      if (vocabList) {
        return vocabList
      }
      node = node.parentElement
    }
  }
  return null
}

function parseVocabItem(li) {
  const word = li.querySelector('span.font-extrabold')?.textContent?.trim() || ''
  const partOfSpeech = li.querySelector('span.italic')?.textContent?.trim().replace(/[()]/g, '') || ''
  const cefr = Array.from(li.querySelectorAll('span'))
    .map((span) => span.textContent?.trim() || '')
    .find((text) => /^(A1|A2|B1|B2|C1|C2)$/i.test(text)) || ''
  const pronunciation_us = (() => {
    const match = li.textContent?.match(/US\s*\/([^\/]+)\//)
    return match ? match[1].trim() : ''
  })()
  const pronunciation_uk = (() => {
    const match = li.textContent?.match(/UK\s*\/([^\/]+)\//)
    return match ? match[1].trim() : ''
  })()
  const meaning = li.querySelector('div > div:not(.italic)')?.textContent?.trim() || ''
  const example = li.querySelector('div.pl-3 .italic')?.textContent?.trim().replace(/^['"“”]+|['"“”]+$/g, '') || ''
  const translation = Array.from(li.querySelectorAll('div.pl-3 > div'))
    .map((div) => div.textContent?.trim() || '')
    .filter((text) => text && !/^['"“”]/.test(text))
    .slice(1, 2)[0] || ''
  const phrases = Array.from(li.querySelectorAll('div span'))
    .filter((span) => span.textContent && /Cụm:/i.test(span.parentElement?.textContent || ''))
    .map((span) => span.textContent?.trim() || '')
    .filter(Boolean)
  const approxMatch = li.textContent?.match(/≈\s*([^\n]+)/)

  return {
    word,
    partOfSpeech,
    cefr,
    pronunciation_us,
    pronunciation_uk,
    meaning,
    example,
    translation,
    phrases,
    approx: approxMatch ? approxMatch[1].trim() : '',
    rawText: li.textContent.trim().replace(/\s+/g, ' '),
  }
}

function parseVocabList(list) {
  if (!list) return []
  return Array.from(list.querySelectorAll('li')).map(parseVocabItem)
}

function scanPage() {
  const visibleText = getVisibleTextNodes()
    .map((node) => node.nodeValue.trim())
    .filter(Boolean)
    .join(' ')

  const words = extractWords(visibleText)
  const uniqueWords = Array.from(new Set(words.map((w) => w.toLowerCase())))
  const filtered = uniqueWords.filter((w) => !/^[0-9]+$/.test(w)).slice(0, 200)

  const vocabList = findVocabSection()
  const vocabCards = parseVocabList(vocabList)

  const results = {
    pageTitle: document.title,
    url: window.location.href,
    visibleTextNodes: visibleText.length,
    wordCount: words.length,
    uniqueCandidateWords: filtered,
    vocabSectionFound: Boolean(vocabList),
    vocabCards,
    sampleText: visibleText.slice(0, 2000),
  }

  console.group('VocKO TOEIC Scanner')
  console.log('Scan results:', results)
  console.groupEnd()
  return results
}

window.addEventListener('load', () => {
  const scanResults = scanPage()
  window.__vocKoToeicScanner = scanResults
})

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type === 'scanPage') {
    const results = scanPage()
    sendResponse({ success: true, results })
    return true
  }
  return false
})

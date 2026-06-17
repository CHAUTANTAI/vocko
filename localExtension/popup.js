const scanButton = document.getElementById('scanButton')
const output = document.getElementById('output')

function renderResult(result) {
  if (!result) {
    output.textContent = 'No result received.'
    return
  }
  const { pageTitle, url, visibleTextNodes, wordCount, uniqueCandidateWords, candidateElements } = result
  const lines = [
    `Page: ${pageTitle}`,
    `URL: ${url}`,
    `Visible text length: ${visibleTextNodes}`,
    `Total extracted words: ${wordCount}`,
    `Candidate words (${uniqueCandidateWords.length}): ${uniqueCandidateWords.slice(0, 40).join(', ')}`,
    '',
    `Candidate page elements (${candidateElements.length}):`,
  ]
  candidateElements.slice(0, 10).forEach((item, index) => {
    lines.push(`${index + 1}. <${item.tag}> id="${item.id}" class="${item.class}" text="${item.text}"`)
  })
  output.textContent = lines.join('\n')
}

async function scanCurrentTab() {
  scanButton.disabled = true
  output.textContent = 'Scanning page...'

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true })
  if (!tab?.id) {
    output.textContent = 'Unable to find active tab.'
    scanButton.disabled = false
    return
  }

  chrome.tabs.sendMessage(tab.id, { type: 'scanPage' }, (response) => {
    if (chrome.runtime.lastError) {
      output.textContent = 'Content script not available on this page. Reload the page or try a different tab.'
      scanButton.disabled = false
      return
    }
    if (response?.success) {
      renderResult(response.results)
    } else {
      output.textContent = 'Scan failed.'
    }
    scanButton.disabled = false
  })
}

scanButton.addEventListener('click', scanCurrentTab)

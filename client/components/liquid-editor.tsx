"use client"

import React, { useEffect, useRef } from 'react'
import Editor, { Monaco } from '@monaco-editor/react'
import { useTheme } from 'next-themes'

interface LiquidEditorProps {
  value: string
  onChange: (value: string | undefined) => void
  placeholder?: string
  height?: string
  readOnly?: boolean
  className?: string
}

// Define Liquid language syntax for Monaco
function configureLiquidLanguage(monaco: Monaco) {
  // Register the Liquid language if not already registered
  if (!monaco.languages.getLanguages().some(({ id }) => id === 'liquid')) {
    monaco.languages.register({ id: 'liquid' })

    // Set language configuration
    monaco.languages.setLanguageConfiguration('liquid', {
      comments: {
        blockComment: ['{% comment %}', '{% endcomment %}']
      },
      brackets: [
        ['{%', '%}'],
        ['{{', '}}'],
        ['{', '}'],
        ['[', ']'],
        ['(', ')']
      ],
      autoClosingPairs: [
        { open: '{%', close: '%}' },
        { open: '{{', close: '}}' },
        { open: '[', close: ']' },
        { open: '(', close: ')' },
        { open: '"', close: '"' },
        { open: "'", close: "'" }
      ],
      surroundingPairs: [
        { open: '{%', close: '%}' },
        { open: '{{', close: '}}' },
        { open: '[', close: ']' },
        { open: '(', close: ')' },
        { open: '"', close: '"' },
        { open: "'", close: "'" }
      ]
    })

    // Define Liquid syntax highlighting
    monaco.languages.setMonarchTokensProvider('liquid', {
      defaultToken: '',
      tokenPostfix: '.liquid',

      keywords: [
        'if', 'elsif', 'else', 'endif', 'unless', 'endunless',
        'for', 'endfor', 'in', 'break', 'continue',
        'case', 'when', 'endcase',
        'block', 'endblock', 'extends', 'include',
        'assign', 'capture', 'endcapture',
        'comment', 'endcomment',
        'raw', 'endraw',
        'liquid', 'endliquid'
      ],

      operators: [
        '==', '!=', '<', '>', '<=', '>=',
        'and', 'or', 'contains'
      ],

      // Liquid filters
      filters: [
        'abs', 'append', 'at_least', 'at_most', 'capitalize', 'ceil', 'compact',
        'concat', 'date', 'default', 'divided_by', 'downcase', 'escape', 'escape_once',
        'first', 'floor', 'join', 'last', 'lstrip', 'map', 'minus', 'modulo',
        'newline_to_br', 'plus', 'prepend', 'remove', 'remove_first', 'replace',
        'replace_first', 'reverse', 'round', 'rstrip', 'size', 'slice', 'sort',
        'sort_natural', 'split', 'strip', 'strip_html', 'strip_newlines', 'times',
        'truncate', 'truncatewords', 'uniq', 'upcase', 'url_decode', 'url_encode',
        'where', 'parse_date', 'iso_datetime', 'add_minutes' // Custom filters
      ],

      tokenizer: {
        root: [
          // Liquid tags
          [/\{%-?\s*/, { token: 'delimiter.liquid', next: '@liquidTag' }],
          
          // Liquid output
          [/\{\{-?\s*/, { token: 'delimiter.liquid', next: '@liquidOutput' }],
          
          // JSON
          [/{/, 'delimiter.bracket.json', '@json'],
          
          // Other content
          [/[^{]+/, '']
        ],

        liquidTag: [
          [/\s*-?%\}/, { token: 'delimiter.liquid', next: '@pop' }],
          [/\b(if|elsif|else|endif|unless|endunless|for|endfor|case|when|endcase|assign|capture|endcapture|comment|endcomment|raw|endraw)\b/, 'keyword.liquid'],
          [/\b(in|and|or|contains)\b/, 'operator.liquid'],
          [/"([^"\\]|\\.)*"/, 'string.liquid'],
          [/'([^'\\]|\\.)*'/, 'string.liquid'],
          [/\b\d+\b/, 'number.liquid'],
          [/\b(true|false|nil)\b/, 'constant.liquid'],
          [/[a-zA-Z_]\w*/, 'variable.liquid']
        ],

        liquidOutput: [
          [/\s*-?\}\}/, { token: 'delimiter.liquid', next: '@pop' }],
          [/\|/, 'operator.liquid'],
          [/\b(abs|append|at_least|at_most|capitalize|ceil|compact|concat|date|default|divided_by|downcase|escape|escape_once|first|floor|join|last|lstrip|map|minus|modulo|newline_to_br|plus|prepend|remove|remove_first|replace|replace_first|reverse|round|rstrip|size|slice|sort|sort_natural|split|strip|strip_html|strip_newlines|times|truncate|truncatewords|uniq|upcase|url_decode|url_encode|where|parse_date|iso_datetime|add_minutes)\b/, 'support.function.liquid'],
          [/"([^"\\]|\\.)*"/, 'string.liquid'],
          [/'([^'\\]|\\.)*'/, 'string.liquid'],
          [/\b\d+\b/, 'number.liquid'],
          [/\b(true|false|nil)\b/, 'constant.liquid'],
          [/[a-zA-Z_][\w.]*/, 'variable.liquid']
        ],

        json: [
          [/"([^"\\]|\\.)*"/, 'string.json'],
          [/\b\d+(\.\d+)?([eE][+-]?\d+)?\b/, 'number.json'],
          [/\b(true|false|null)\b/, 'constant.json'],
          [/[{}[\],:]/, 'delimiter.bracket.json'],
          [/}/, 'delimiter.bracket.json', '@pop']
        ]
      }
    })
  }
}

export function LiquidEditor({
  value,
  onChange,
  placeholder,
  height = '200px',
  readOnly = false,
  className
}: LiquidEditorProps) {
  const { theme } = useTheme()
  const editorRef = useRef<any>(null)

  const handleEditorWillMount = (monaco: Monaco) => {
    configureLiquidLanguage(monaco)
  }

  const handleEditorDidMount = (editor: any, monaco: Monaco) => {
    editorRef.current = editor
    
    // Set editor options
    editor.updateOptions({
      minimap: { enabled: false },
      lineNumbers: 'on',
      roundedSelection: false,
      scrollBeyondLastLine: false,
      readOnly,
      automaticLayout: true,
      formatOnPaste: true,
      formatOnType: true,
      wordWrap: 'on',
      fontSize: 13,
      tabSize: 2,
      insertSpaces: true,
      folding: true,
      showFoldingControls: 'always'
    })
  }

  return (
    <div className={className}>
      <Editor
        height={height}
        defaultLanguage="liquid"
        theme={theme === 'dark' ? 'vs-dark' : 'vs'}
        value={value}
        onChange={onChange}
        beforeMount={handleEditorWillMount}
        onMount={handleEditorDidMount}
        options={{
          minimap: { enabled: false },
          lineNumbers: 'on',
          roundedSelection: false,
          scrollBeyondLastLine: false,
          readOnly,
          automaticLayout: true,
          wordWrap: 'on',
          fontSize: 13,
          tabSize: 2,
          insertSpaces: true,
          folding: true,
          showFoldingControls: 'always',
          placeholder
        }}
      />
    </div>
  )
}
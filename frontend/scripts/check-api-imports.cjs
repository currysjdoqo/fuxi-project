#!/usr/bin/env node
/**
 * 检查「调用了 src/api/index.js 导出的函数，却没有 import」的情况。
 *
 * 背景：把科目下拉改成文件夹分组后，Import.vue / Trash.vue / Friends.vue 的调用点
 * 从 getSubjects() 换成了 getFoldersWithSubjects()，但 import 语句没跟着改。
 * Vite 构建不会报错（未声明的标识符在打包后仍然是合法代码），只有浏览器运行时
 * 才抛 `ReferenceError: getFoldersWithSubjects is not defined`，页面表现就是
 * 下拉框「无数据 / No data」。这个脚本把这类问题提前到命令行。
 *
 * 用法：npm run check:imports  （在 frontend/ 目录）
 */
const fs = require('fs')
const path = require('path')

const root = path.resolve(__dirname, '..')
const apiIndex = path.join(root, 'src', 'api', 'index.js')
const srcDir = path.join(root, 'src')

const apiSource = fs.readFileSync(apiIndex, 'utf8')
const exported = [...apiSource.matchAll(/export\s+const\s+(\w+)\s*=/g)].map((m) => m[1])

const collectFiles = (dir, acc = []) => {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name)
    if (entry.isDirectory()) collectFiles(full, acc)
    else if (/\.(vue|js)$/.test(entry.name)) acc.push(full)
  }
  return acc
}

const problems = []
for (const file of collectFiles(srcDir)) {
  if (file === apiIndex) continue
  const source = fs.readFileSync(file, 'utf8')
  if (!/from\s+['"][^'"]*\/api['"]/.test(source) && !/from\s+['"]\.\/api['"]/.test(source)) continue

  const imported = new Set()
  for (const m of source.matchAll(/import\s*\{([^}]+)\}\s*from\s*['"][^'"]*api['"]/g)) {
    for (const part of m[1].split(',')) {
      const name = part.trim().split(/\s+as\s+/)[0].trim()
      if (name) imported.add(name)
    }
  }

  for (const name of exported) {
    const called = new RegExp(`(?<![\\w.])${name}\\s*\\(`).test(source)
    if (called && !imported.has(name)) {
      problems.push(`${path.relative(root, file)}: 调用了 ${name}() 但没有从 api 导入`)
    }
  }
}

if (problems.length) {
  console.error('发现 api 函数「用了但没导入」的问题：')
  for (const line of problems) console.error('  - ' + line)
  console.error('\n这类问题构建时不会报错，浏览器运行时会抛 ReferenceError，页面表现为「无数据」。')
  process.exit(1)
}

console.log(`api 导入检查通过：${exported.length} 个导出函数，未发现漏导入。`)

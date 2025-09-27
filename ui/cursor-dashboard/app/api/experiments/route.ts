import { NextResponse } from 'next/server'
import { readdir, readFile } from 'fs/promises'
import { join } from 'path'

export async function GET() {
  try {
    // Read experiments directory
    const experimentsDir = join(process.cwd(), '..', '..', 'experiments', 'out')
    
    let experiments = []
    try {
      const dirs = await readdir(experimentsDir, { withFileTypes: true })
      const experimentDirs = dirs
        .filter(dirent => dirent.isDirectory())
        .sort((a, b) => b.name.localeCompare(a.name)) // Most recent first
        .slice(0, 10) // Limit to 10 most recent
      
      for (const dir of experimentDirs) {
        try {
          const summaryPath = join(experimentsDir, dir.name, 'summary.json')
          const summary = JSON.parse(await readFile(summaryPath, 'utf8'))
          experiments.push({
            timestamp: dir.name,
            ...summary
          })
        } catch (e) {
          // Skip experiments without valid summary.json
          continue
        }
      }
    } catch (e) {
      // No experiments directory or empty
      experiments = []
    }
    
    return NextResponse.json({ experiments })
  } catch (error) {
    console.error('Error reading experiments:', error)
    return NextResponse.json({ experiments: [] })
  }
}

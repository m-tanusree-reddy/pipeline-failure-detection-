import { useState, useEffect } from "react"
import { Search, X } from "lucide-react"

const LOG_LINES = [
  { text: "[INFO] Starting Agent v2.4.1...", type: "info" },
  { text: "[INFO] Monitoring file stream...", type: "info" },
  { text: "[DEBUG] Buffer allocated: 256MB", type: "default" },
  { text: "[SYSTEM] Handshake with GitHub Actions API established", type: "default" },
  { text: "[AI] Loading semantic model 'debugger-instruct-v2'...", type: "ai" },
  { text: "[INFO] File uploaded: log_export_v4.log", type: "info" },
  { text: "[PROCESS] Beginning initial parse...", type: "default" },
  { text: "[WARN] Found 14 unhandled exceptions in stream", type: "warn" },
  { text: "[INFO] Vectorizing chunk 1/140...", type: "info" },
  { text: "[INFO] Vectorizing chunk 42/140...", type: "info" },
  { text: "[AI] Comparing failure patterns with repository history...", type: "ai" },
  { text: "[SUCCESS] Match found: Commit #af42c1 'refactor: network layer'", type: "success" },
  { text: "[PROCESS] Building causal graph...", type: "default" },
  { text: "[INFO] Evidence collected from 4 sub-modules", type: "info" },
  { text: "[AI] Finalizing root cause report...", type: "ai" }
]

export default function TerminalOutput({ active }: { active: boolean }) {
  const [lines, setLines] = useState<{text: string, type: string, time: string}[]>([])

  useEffect(() => {
    if (!active) return
    let currentLine = 0
    const interval = setInterval(() => {
      if (currentLine >= LOG_LINES.length) {
        clearInterval(interval)
        return
      }
      const time = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
      setLines(prev => [...prev, { ...LOG_LINES[currentLine], time }])
      currentLine++
    }, 800)

    return () => clearInterval(interval)
  }, [active])

  return (
    <footer className="h-64 bg-card/60 backdrop-blur-md border-t border-border overflow-hidden flex flex-col shadow-2xl relative">
      <div className="absolute inset-0 pointer-events-none opacity-20 bg-[linear-gradient(to_bottom,transparent_50%,rgba(175,198,255,0.05)_50%)] bg-[length:100%_4px]"></div>
      
      {/* Terminal Header */}
      <div className="bg-[#141b2d] px-6 py-2 flex items-center gap-6 border-b border-white/5 z-10">
        <div className="flex gap-6 border-b-2 border-primary -mb-[9px] pb-[8px]">
          <span className="text-primary font-sans text-xs font-semibold tracking-wider uppercase cursor-pointer">TERMINAL</span>
        </div>
        <span className="text-muted-foreground font-sans text-xs font-semibold tracking-wider uppercase hover:text-foreground cursor-pointer transition-colors">DEBUG CONSOLE</span>
        <span className="text-muted-foreground font-sans text-xs font-semibold tracking-wider uppercase hover:text-foreground cursor-pointer transition-colors">OUTPUT</span>
        
        <div className="ml-auto flex gap-4">
          <Search className="text-muted-foreground w-4 h-4 hover:text-foreground cursor-pointer transition-colors" />
          <X className="text-muted-foreground w-4 h-4 hover:text-foreground cursor-pointer transition-colors" />
        </div>
      </div>
      
      {/* Terminal Content */}
      <div className="flex-1 bg-[#05070A] p-6 font-mono text-sm overflow-y-auto space-y-2 z-10 flex flex-col no-scrollbar">
        <div className="text-muted-foreground opacity-60">System initialized. Waiting for log input...</div>
        
        {lines.map((line, i) => (
          <div key={i} className="flex gap-4 animate-in fade-in slide-in-from-left-1 duration-300">
            <span className="text-muted-foreground/30 shrink-0">[{line.time}]</span>
            <span className={
              line.type === 'warn' ? 'text-[#d2bbff]' :
              line.type === 'ai' ? 'text-[#6bff8f]' :
              line.type === 'error' ? 'text-destructive' :
              line.type === 'success' ? 'text-[#4ae176]' :
              'text-foreground'
            }>
              {line.text}
            </span>
          </div>
        ))}
        
        <div className="text-primary flex gap-4 mt-auto">
          <span>$</span>
          <span className="animate-pulse">_</span>
        </div>
      </div>
    </footer>
  )
}

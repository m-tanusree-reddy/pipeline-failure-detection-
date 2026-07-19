import { useEffect, useState } from "react"
import { 
  FileText, Network, Search, Database, Brain, ShieldCheck, Activity
} from "lucide-react"
import { cn } from "../../lib/utils"

const STEPS = [
  { id: 'parse', label: 'Parsing Logs', icon: FileText, time: '1.2s' },
  { id: 'classify', label: 'Error Classification', icon: Network, time: '0.8s' },
  { id: 'plan', label: 'Planning', icon: Search, time: '2.1s' },
  { id: 'embed', label: 'Creating Embeddings', icon: Database, time: '3.2s' },
  { id: 'retrieve', label: 'Semantic Retrieval', icon: Brain, time: '2.4s' },
  { id: 'critic', label: 'Critic Verification', icon: ShieldCheck, time: '1.8s' },
  { id: 'report', label: 'Report Generation', icon: FileText, time: '1.2s' }
]

interface PipelineProgressProps {
  onComplete: () => void
}

export default function PipelineProgress({ onComplete }: PipelineProgressProps) {
  const [currentStep, setCurrentStep] = useState(0)

  useEffect(() => {
    if (currentStep >= STEPS.length) {
      setTimeout(onComplete, 1000)
      return
    }

    const timer = setTimeout(() => {
      setCurrentStep(s => s + 1)
    }, 1200)

    return () => clearTimeout(timer)
  }, [currentStep, onComplete])

  const progressPercent = (currentStep / (STEPS.length - 1)) * 100

  return (
    <div className="flex flex-col gap-10 p-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-sans text-3xl font-bold text-foreground">Analysis Pipeline</h1>
          <p className="text-muted-foreground font-sans">Processing <strong className="text-foreground">log_export_v4.log</strong> (24.8 MB)</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-[#6bff8f] animate-pulse"></div>
          <span className="text-[#6bff8f] font-sans text-xs font-semibold tracking-wider uppercase">LIVE PROCESSING</span>
        </div>
      </div>

      <div className="relative py-16 overflow-x-auto no-scrollbar">
        <div className="flex items-start min-w-max gap-4 relative">
          
          {/* Connector Line */}
          <div className="absolute top-8 left-0 h-1 bg-border w-full -z-10 rounded-full overflow-hidden">
            <div 
              className="h-full bg-primary transition-all duration-1000" 
              style={{ width: `${progressPercent}%` }}
            ></div>
          </div>
          
          {/* Stages */}
          <div className="flex gap-10">
            {STEPS.map((step, idx) => {
              const isActive = idx === currentStep
              const isPast = idx < currentStep
              const Icon = step.icon
              
              return (
                <div key={step.id} className={cn("flex flex-col items-center gap-6 w-32 transition-all duration-500", !isActive && !isPast && "opacity-40")}>
                  <div className={cn(
                    "w-16 h-16 rounded-full bg-popover flex items-center justify-center border transition-all duration-500",
                    (isActive || isPast) ? "border-primary shadow-[0_0_15px_rgba(175,198,255,0.3)]" : "border-white/10"
                  )}>
                    <Icon className={cn("w-6 h-6", (isActive || isPast) ? "text-primary" : "text-muted-foreground")} />
                  </div>
                  <div className="text-center">
                    <p className={cn("font-sans text-xs font-semibold tracking-wider uppercase leading-tight mb-1", (isActive || isPast) ? "text-foreground" : "text-muted-foreground")}>
                      {step.label}
                    </p>
                    <span className="font-mono text-xs text-muted-foreground/60">{step.time}</span>
                  </div>
                </div>
              )
            })}
          </div>

        </div>
      </div>
      
      {/* Dashboard Insights Preview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 flex-1 mb-8">
        <div className="md:col-span-2 bg-card/60 backdrop-blur-md border border-white/10 rounded-xl p-6 flex flex-col">
          <div className="flex items-center justify-between mb-6">
            <h3 className="font-sans text-xl font-bold text-foreground flex items-center gap-2">
              <Activity className="text-primary w-5 h-5" />
              Intelligent Insight
            </h3>
            <span className="font-mono text-sm text-primary">v2.4 Engine</span>
          </div>
          <div className="flex-1 flex items-center justify-center text-center p-16">
            <div>
              <p className="text-muted-foreground font-sans mb-4">AI is currently analyzing 14,000 log lines...</p>
              <div className="flex gap-2 justify-center">
                <div className="h-1 w-12 bg-primary rounded-full animate-pulse"></div>
                <div className="h-1 w-12 bg-primary/40 rounded-full animate-pulse delay-75"></div>
                <div className="h-1 w-12 bg-primary/20 rounded-full animate-pulse delay-150"></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

import { useState } from "react"
import { Terminal } from "lucide-react"
import { Link } from "react-router-dom"
import Sidebar from "../components/layout/Sidebar"
import UploadArea from "../components/dashboard/UploadArea"
import PipelineProgress from "../components/dashboard/PipelineProgress"
import TerminalOutput from "../components/dashboard/TerminalOutput"
import FailureReport from "../components/dashboard/FailureReport"
import EvidenceCards from "../components/dashboard/EvidenceCards"

export default function Dashboard() {
  // State: 'upload' -> 'processing' -> 'results'
  const [status, setStatus] = useState<'upload' | 'processing' | 'results'>('upload')

  const handleUpload = () => {
    setStatus('processing')
  }

  const handleProcessingComplete = () => {
    setStatus('results')
  }

  return (
    <div className="bg-background text-foreground min-h-screen flex flex-col overflow-hidden">
      {/* Top Navigation Bar */}
      <header className="fixed top-0 w-full z-50 bg-background/60 backdrop-blur-md border-b border-border shadow-sm">
        <div className="flex justify-between items-center h-16 px-6 max-w-[1440px] mx-auto">
          <div className="flex items-center gap-4">
            <Terminal className="text-primary w-8 h-8" />
            <span className="font-sans text-2xl font-bold text-foreground">CI Debug Agent</span>
          </div>
          <nav className="hidden md:flex gap-6 items-center">
            <Link to="/" className="text-muted-foreground hover:text-foreground transition-colors font-sans text-base">Home</Link>
            <Link to="/architecture" className="text-muted-foreground hover:text-foreground transition-colors font-sans text-base">Architecture</Link>
            <Link to="/about" className="text-muted-foreground hover:text-foreground transition-colors font-sans text-base">About</Link>
            <Link to="/dashboard" className="text-primary font-bold border-b-2 border-primary pb-1 font-sans text-base">Dashboard</Link>
          </nav>
          <div className="flex items-center gap-4">
            <button className="bg-primary/10 text-primary px-4 py-1.5 rounded hover:bg-primary/20 transition-all duration-200 active:scale-95 flex items-center gap-2 font-sans text-sm font-bold">
              GitHub
            </button>
          </div>
        </div>
      </header>

      {/* Sidebar & Main Content */}
      <div className="flex flex-1 pt-16 h-full overflow-hidden">
        <Sidebar />
        
        {/* Main Stage */}
        <main className="ml-[280px] flex-1 flex flex-col p-8 bg-background relative overflow-hidden">
          {/* Atmospheric BG Effect */}
          <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-primary/5 rounded-full blur-[120px] -z-10 pointer-events-none"></div>
          
          {/* Content Area based on State */}
          {status === 'upload' && (
            <UploadArea onUpload={handleUpload} />
          )}

          {status === 'processing' && (
            <div className="flex-1 overflow-y-auto no-scrollbar">
              <PipelineProgress onComplete={handleProcessingComplete} />
            </div>
          )}

          {status === 'results' && (
            <div className="flex-1 overflow-y-auto no-scrollbar pb-8">
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 max-w-[1440px] mx-auto">
                <FailureReport />
                <EvidenceCards />
              </div>
            </div>
          )}
          
          {/* Terminal Output */}
          {(status === 'processing' || status === 'results') && (
            <TerminalOutput active={true} />
          )}
        </main>
      </div>
    </div>
  )
}

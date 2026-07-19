import { Link } from "react-router-dom"
import { BarChart3, GitFork, TerminalSquare, Settings, Activity } from "lucide-react"

export default function Sidebar() {
  return (
    <aside className="fixed left-0 top-16 h-[calc(100vh-64px)] w-[280px] bg-card border-r border-border flex flex-col py-6 px-4 z-40">
      <div className="mb-10 px-4">
        <div className="flex items-center gap-4 mb-2">
          <div className="w-10 h-10 rounded bg-primary/20 flex items-center justify-center">
            <Activity className="text-primary w-6 h-6" />
          </div>
          <div>
            <p className="font-sans text-base font-bold text-foreground">Project Alpha</p>
            <p className="font-sans text-[10px] uppercase tracking-wider font-semibold text-muted-foreground">main-branch</p>
          </div>
        </div>
      </div>
      
      <nav className="flex-1 space-y-2">
        <Link to="/dashboard" className="flex items-center gap-4 px-4 py-3 rounded-lg text-primary-container font-bold border-r-4 border-primary-container bg-primary/10 transition-all duration-300">
          <BarChart3 className="w-5 h-5" />
          <span className="font-sans text-xs uppercase tracking-wider font-semibold">Overview</span>
        </Link>
        <Link to="#" className="flex items-center gap-4 px-4 py-3 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-all duration-300">
          <GitFork className="w-5 h-5" />
          <span className="font-sans text-xs uppercase tracking-wider font-semibold">Pipelines</span>
        </Link>
        <Link to="#" className="flex items-center gap-4 px-4 py-3 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-all duration-300">
          <TerminalSquare className="w-5 h-5" />
          <span className="font-sans text-xs uppercase tracking-wider font-semibold">Logs</span>
        </Link>
        <Link to="#" className="flex items-center gap-4 px-4 py-3 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-all duration-300">
          <Settings className="w-5 h-5" />
          <span className="font-sans text-xs uppercase tracking-wider font-semibold">Settings</span>
        </Link>
      </nav>
      
      <div className="mt-auto space-y-6 p-4">
        <div className="bg-[#141b2d] p-4 rounded border border-white/5">
          <p className="text-muted-foreground font-sans text-[10px] mb-4 uppercase tracking-widest font-semibold">Stats Overview</p>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-muted-foreground font-sans text-sm">Pipelines</span>
              <span className="text-primary font-bold">1,284</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-muted-foreground font-sans text-sm">Avg. Analysis</span>
              <span className="text-primary font-bold">12.4s</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-muted-foreground font-sans text-sm">Documents</span>
              <span className="text-primary font-bold">45.2k</span>
            </div>
          </div>
        </div>
        <button className="w-full bg-primary text-primary-foreground py-4 font-bold rounded-lg hover:brightness-110 transition-all active:scale-95 shadow-[0_0_15px_rgba(175,198,255,0.2)]">
          Analyze Now
        </button>
      </div>
    </aside>
  )
}

import { motion } from "framer-motion"
import { ArrowRight, Terminal, Network, GitPullRequest, Search, FileText } from "lucide-react"
import { useNavigate } from "react-router-dom"

export default function Hero() {
  const navigate = useNavigate()

  return (
    <section className="relative min-h-[900px] flex items-center overflow-hidden pt-16">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-primary/5 via-background to-background pointer-events-none"></div>
      
      <div className="relative z-10 max-w-[1440px] mx-auto px-6 w-full grid grid-cols-1 lg:grid-cols-2 gap-16 items-center py-16">
        
        {/* Left Content */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="flex flex-col gap-6"
        >
          <div className="inline-flex items-center gap-2 bg-primary/10 border border-primary/20 px-4 py-1 rounded-full w-fit">
            <span className="w-2 h-2 rounded-full bg-[#4ae176] animate-pulse"></span>
            <span className="font-sans text-xs font-semibold tracking-wider text-primary uppercase">v2.4.0 Engine Active</span>
          </div>
          
          <h1 className="font-sans text-5xl md:text-6xl font-bold text-foreground leading-tight tracking-tight">
            AI-Powered CI/CD <br/><span className="text-primary">Failure Investigation</span>
          </h1>
          
          <p className="font-sans text-lg text-muted-foreground max-w-xl">
            Upload a failed GitHub Actions log and let autonomous AI agents determine the root cause, retrieve supporting evidence, validate conclusions, and generate a comprehensive failure report.
          </p>
          
          <div className="flex flex-wrap gap-4 pt-4">
            <motion.button 
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => navigate('/dashboard')}
              className="bg-primary text-primary-foreground font-bold py-4 px-8 rounded-full shadow-[0_0_20px_0_rgba(175,198,255,0.15)] transition-all flex items-center gap-2"
            >
              Analyze Pipeline
              <ArrowRight className="w-5 h-5" />
            </motion.button>
            
            <motion.button 
              whileHover={{ backgroundColor: "rgba(255,255,255,0.05)" }}
              className="border border-border text-foreground font-bold py-4 px-8 rounded-full transition-all"
            >
              View Demo
            </motion.button>
          </div>
        </motion.div>

        {/* Right Content: Pipeline Visualization */}
        <motion.div 
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.8, delay: 0.2 }}
          className="relative p-8 bg-card/70 backdrop-blur-md border border-white/10 rounded-2xl hidden lg:block overflow-hidden shadow-2xl"
        >
          <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent"></div>
          
          <div className="relative grid grid-cols-3 gap-y-12 gap-x-4 items-center">
            
            {/* Stage 1 */}
            <div className="flex flex-col items-center gap-2">
              <div className="w-12 h-12 rounded-lg bg-popover border border-border flex items-center justify-center text-primary">
                <Terminal className="w-6 h-6" />
              </div>
              <span className="font-sans text-xs font-semibold tracking-wider text-muted-foreground uppercase">GitHub Actions</span>
            </div>
            
            <div className="relative h-px w-full">
              <div className="absolute top-1/2 w-full h-[2px] bg-gradient-to-r from-transparent via-primary/50 to-transparent animate-[flow_3s_linear_infinite]" style={{ backgroundSize: '200% 100%' }}></div>
            </div>
            
            <div className="flex flex-col items-center gap-2">
              <div className="w-12 h-12 rounded-lg bg-popover border border-border flex items-center justify-center text-primary">
                <Network className="w-6 h-6" />
              </div>
              <span className="font-sans text-xs font-semibold tracking-wider text-muted-foreground uppercase">Parser</span>
            </div>
            
            {/* Row 2 */}
            <div className="flex flex-col items-center gap-2">
              <div className="w-12 h-12 rounded-lg bg-popover border border-border flex items-center justify-center text-primary">
                <GitPullRequest className="w-6 h-6" />
              </div>
              <span className="font-sans text-xs font-semibold tracking-wider text-muted-foreground uppercase">Classifier</span>
            </div>
            
            <div className="relative h-px w-full">
              <div className="absolute top-1/2 w-full h-[2px] bg-gradient-to-r from-transparent via-primary/50 to-transparent animate-[flow_3s_linear_infinite]" style={{ backgroundSize: '200% 100%' }}></div>
            </div>
            
            <div className="flex flex-col items-center gap-2">
              <div className="w-12 h-12 rounded-lg bg-popover border border-border flex items-center justify-center text-primary">
                <Search className="w-6 h-6" />
              </div>
              <span className="font-sans text-xs font-semibold tracking-wider text-muted-foreground uppercase">Planner</span>
            </div>

            {/* Row 3 */}
            <div className="flex flex-col items-center gap-2">
              <div className="w-12 h-12 rounded-lg bg-popover border border-border flex items-center justify-center text-primary">
                <DatabaseIcon />
              </div>
              <span className="font-sans text-xs font-semibold tracking-wider text-muted-foreground uppercase">Vector DB</span>
            </div>
            
            <div className="relative h-px w-full">
              <div className="absolute top-1/2 w-full h-[2px] bg-gradient-to-r from-transparent via-primary/50 to-transparent animate-[flow_3s_linear_infinite]" style={{ backgroundSize: '200% 100%' }}></div>
            </div>
            
            <div className="flex flex-col items-center gap-2">
              <div className="w-12 h-12 rounded-lg bg-primary/20 border border-primary/40 flex items-center justify-center text-primary shadow-[0_0_15px_0_rgba(175,198,255,0.2)]">
                <BrainIcon />
              </div>
              <span className="font-sans text-xs font-semibold tracking-wider text-primary uppercase">LLM Engine</span>
            </div>
            
            {/* Row 4 */}
            <div className="flex flex-col items-center gap-2">
              <div className="w-12 h-12 rounded-lg bg-popover border border-border flex items-center justify-center text-primary">
                <FactCheckIcon />
              </div>
              <span className="font-sans text-xs font-semibold tracking-wider text-muted-foreground uppercase">Critic</span>
            </div>
            
            <div className="relative h-px w-full">
              <div className="absolute top-1/2 w-full h-[2px] bg-gradient-to-r from-transparent via-primary/50 to-transparent animate-[flow_3s_linear_infinite]" style={{ backgroundSize: '200% 100%' }}></div>
            </div>
            
            <div className="flex flex-col items-center gap-2">
              <div className="w-12 h-12 rounded-lg bg-[#4ae176]/20 border border-[#4ae176]/40 flex items-center justify-center text-[#4ae176]">
                <FileText className="w-6 h-6" />
              </div>
              <span className="font-sans text-xs font-semibold tracking-wider text-[#4ae176] uppercase">Final Report</span>
            </div>

          </div>
        </motion.div>
      </div>

      <style>{`
        @keyframes flow {
          0% { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }
      `}</style>
    </section>
  )
}

function DatabaseIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5V19A9 3 0 0 0 21 19V5"/><path d="M3 12A9 3 0 0 0 21 12"/></svg>
  )
}

function BrainIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588A4 4 0 1 0 12 18Z"/><path d="M12 5a3 3 0 1 1 5.997.125 4 4 0 0 1 2.526 5.77 4 4 0 0 1-.556 6.588A4 4 0 1 1 12 18Z"/><path d="M15 13a4.5 4.5 0 0 1-3-4 4.5 4.5 0 0 1-3 4"/><path d="M17.599 6.5a3 3 0 0 0 .399-1.375"/><path d="M6.002 5.125A3 3 0 0 0 6.401 6.5"/><path d="M3.477 10.896a4 4 0 0 1 .585-.396"/><path d="M19.938 10.5a4 4 0 0 1 .585.396"/><path d="M6 18a4 4 0 0 1-1.967-.516"/><path d="M19.967 17.484A4 4 0 0 1 18 18"/></svg>
  )
}

function FactCheckIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
  )
}

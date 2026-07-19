import { motion } from "framer-motion"
import { LogIn, BrainCircuit, ShieldCheck, CheckCircle2, Maximize, ZoomIn, ZoomOut } from "lucide-react"
import Navbar from "../components/layout/Navbar"
import Footer from "../components/layout/Footer"

export default function Architecture() {
  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground">
      <Navbar />
      
      <main className="flex-grow pt-24 pb-16 px-6 max-w-[1440px] mx-auto w-full animate-in fade-in slide-in-from-bottom-4 duration-700">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-end mb-8 gap-4">
          <div>
            <h1 className="font-sans text-4xl font-bold text-foreground">Agent Architecture Flow</h1>
            <p className="text-muted-foreground font-sans text-lg mt-2">Interactive trace of the analysis lifecycle</p>
          </div>
          <div className="flex gap-2">
            <button className="p-2 rounded-full hover:bg-muted transition-all bg-card border border-border text-muted-foreground hover:text-foreground">
              <ZoomIn className="w-5 h-5" />
            </button>
            <button className="p-2 rounded-full hover:bg-muted transition-all bg-card border border-border text-muted-foreground hover:text-foreground">
              <ZoomOut className="w-5 h-5" />
            </button>
            <button className="p-2 rounded-full hover:bg-muted transition-all bg-card border border-border text-muted-foreground hover:text-foreground">
              <Maximize className="w-5 h-5" />
            </button>
          </div>
        </div>

        <div className="bg-card/60 backdrop-blur-md border border-white/10 p-12 rounded-2xl min-h-[500px] flex flex-col md:flex-row items-center justify-between gap-8 relative overflow-hidden shadow-2xl">
          <div className="absolute inset-0 opacity-10 pointer-events-none" style={{ backgroundImage: "radial-gradient(#afc6ff 1px, transparent 1px)", backgroundSize: "32px 32px" }}></div>
          
          {/* Node 1 */}
          <motion.div 
            whileHover={{ scale: 1.05 }}
            className="flex flex-col items-center z-10"
          >
            <div className="w-20 h-20 rounded-full bg-popover flex items-center justify-center border-2 border-border shadow-lg mb-4">
              <LogIn className="text-primary w-8 h-8" />
            </div>
            <p className="font-sans text-xs font-semibold tracking-wider uppercase text-foreground">Log Ingestion</p>
          </motion.div>
          
          <div className="hidden md:block flex-1 h-0.5 bg-border relative">
            <div className="absolute top-0 left-0 h-full bg-primary/50 animate-[flow_3s_linear_infinite]" style={{ backgroundSize: '200% 100%' }}></div>
          </div>
          
          {/* Node 2 */}
          <motion.div 
            whileHover={{ scale: 1.05 }}
            className="flex flex-col items-center z-10 relative"
          >
            <div className="absolute -top-3 -right-3 bg-primary text-primary-foreground text-[10px] px-2 py-0.5 font-bold rounded-full animate-bounce">Active</div>
            <div className="w-24 h-24 rounded-2xl bg-popover border-2 border-primary flex items-center justify-center shadow-[0_0_30px_rgba(175,198,255,0.3)] mb-4">
              <BrainCircuit className="text-primary w-10 h-10" />
            </div>
            <p className="font-sans text-xs font-semibold tracking-wider uppercase text-primary">Inference Engine</p>
          </motion.div>

          <div className="hidden md:block flex-1 h-0.5 bg-border"></div>

          {/* Node 3 */}
          <motion.div 
            whileHover={{ scale: 1.05 }}
            className="flex flex-col items-center z-10"
          >
            <div className="w-20 h-20 rounded-full bg-popover flex items-center justify-center border-2 border-border shadow-lg mb-4">
              <ShieldCheck className="text-secondary w-8 h-8" />
            </div>
            <p className="font-sans text-xs font-semibold tracking-wider uppercase text-foreground">Critic Loop</p>
          </motion.div>

          <div className="hidden md:block flex-1 h-0.5 bg-border"></div>

          {/* Node 4 */}
          <motion.div 
            whileHover={{ scale: 1.05 }}
            className="flex flex-col items-center z-10"
          >
            <div className="w-20 h-20 rounded-full bg-popover flex items-center justify-center border-2 border-border shadow-lg mb-4">
              <CheckCircle2 className="text-[#4ae176] w-8 h-8" />
            </div>
            <p className="font-sans text-xs font-semibold tracking-wider uppercase text-foreground">Final Report</p>
          </motion.div>
        </div>
      </main>

      <Footer />
      
      <style>{`
        @keyframes flow {
          0% { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }
      `}</style>
    </div>
  )
}

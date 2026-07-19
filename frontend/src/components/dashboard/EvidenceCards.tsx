import { Bug, FileText, History } from "lucide-react"
import { motion } from "framer-motion"

export default function EvidenceCards() {
  return (
    <div className="lg:col-span-5 space-y-6 overflow-y-auto max-h-full no-scrollbar pb-6 animate-in fade-in slide-in-from-bottom-4 duration-700 delay-200">
      <h2 className="font-sans text-xs font-semibold tracking-wider uppercase text-muted-foreground px-2">Supporting Evidence</h2>
      
      {/* Evidence Card 1 */}
      <motion.div 
        whileHover={{ scale: 1.02, backgroundColor: "rgba(35, 42, 60, 0.8)" }}
        className="bg-card/60 backdrop-blur-md p-4 lg:p-6 rounded-xl border border-white/10 transition-colors group cursor-pointer"
      >
        <div className="flex justify-between items-start mb-2">
          <div className="flex items-center gap-2">
            <Bug className="text-primary w-5 h-5" />
            <span className="font-sans text-xs font-semibold tracking-wider uppercase text-muted-foreground">GitHub Issue #1284</span>
          </div>
          <span className="text-[#4ae176] font-mono text-sm">96% Match</span>
        </div>
        <h4 className="font-sans text-base font-semibold text-foreground mb-2">DB Migration fail: 'Unauthorized' on SSL handshake</h4>
        <p className="font-sans text-sm text-muted-foreground line-clamp-2">"Found that some CI runners require explicit <span className="text-primary font-medium underline underline-offset-4 decoration-primary/30">sslmode</span> parameters in the connection string..."</p>
      </motion.div>

      {/* Evidence Card 2 */}
      <motion.div 
        whileHover={{ scale: 1.02, backgroundColor: "rgba(35, 42, 60, 0.8)" }}
        className="bg-card/60 backdrop-blur-md p-4 lg:p-6 rounded-xl border border-white/10 transition-colors group cursor-pointer"
      >
        <div className="flex justify-between items-start mb-2">
          <div className="flex items-center gap-2">
            <FileText className="text-primary w-5 h-5" />
            <span className="font-sans text-xs font-semibold tracking-wider uppercase text-muted-foreground">System Docs</span>
          </div>
          <span className="text-[#4ae176] font-mono text-sm">82% Match</span>
        </div>
        <h4 className="font-sans text-base font-semibold text-foreground mb-2">V2 Migration Schema Changes</h4>
        <p className="font-sans text-sm text-muted-foreground line-clamp-2">The security layer for <span className="text-primary font-medium underline underline-offset-4 decoration-primary/30">v2.x.x</span> enforces TLS 1.3 by default. Secret managers must update certificates...</p>
      </motion.div>

      {/* Evidence Card 3 */}
      <motion.div 
        whileHover={{ scale: 1.02, backgroundColor: "rgba(35, 42, 60, 0.8)" }}
        className="bg-card/60 backdrop-blur-md p-4 lg:p-6 rounded-xl border border-white/10 transition-colors group cursor-pointer"
      >
        <div className="flex justify-between items-start mb-2">
          <div className="flex items-center gap-2">
            <History className="text-primary w-5 h-5" />
            <span className="font-sans text-xs font-semibold tracking-wider uppercase text-muted-foreground">Historical Log (3d ago)</span>
          </div>
          <span className="text-[#4ae176] font-mono text-sm">74% Match</span>
        </div>
        <h4 className="font-sans text-base font-semibold text-foreground mb-2">Staging Env Failure (Build #452)</h4>
        <p className="font-sans text-sm text-muted-foreground line-clamp-2">Similar trace detected in staging. Fix involved re-rolling <span className="text-primary font-medium underline underline-offset-4 decoration-primary/30">DB secrets</span> on the main branch.</p>
      </motion.div>

      {/* Visualization */}
      <div className="bg-card/60 backdrop-blur-md rounded-xl overflow-hidden relative min-h-[200px] border border-white/10 mt-6">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/10 to-transparent z-10"></div>
        <div className="w-full h-full absolute inset-0 bg-cover bg-center" style={{ backgroundImage: "url('https://lh3.googleusercontent.com/aida-public/AB6AXuCNsDEC1QGx9358vo1C7w6rZBTEYTPrE1GYYB338wauwqobgXDBYfbvWWzOiymUh8O0qu3Gl5HgNwXx75obiTiFhv66Db--q_uZ4qLZ37VypUX1C9BvLHlVnZtAA8BiiI-WKWrctZJRNsLgb8aGmurVpTX1pX9A5Ydhz8EPEBPp85fm6Ihbx9_uBq05AJPNiVYeDc3L-ZYYVN9-nFip99VWMWnKq0wvqrZNbnEbSgF-X0bEgCe-ijbkoys6-vuFE3UV9x8MjGzABQ8')" }}></div>
        <div className="absolute bottom-4 left-4 right-4 bg-background/80 backdrop-blur-md p-2 rounded-md border border-white/10 z-20">
          <p className="font-sans text-xs font-semibold tracking-wider uppercase text-center text-foreground">Contextual Retrieval Map</p>
        </div>
      </div>
    </div>
  )
}

import { motion } from "framer-motion"
import { Terminal, Lightbulb, Search, Network } from "lucide-react"

export default function Features() {
  return (
    <section className="py-24">
      <div className="max-w-[1440px] mx-auto px-6">
        <div className="mb-16 text-center max-w-2xl mx-auto">
          <h2 className="font-sans text-3xl font-bold text-foreground mb-4">Unrivaled Pipeline Intelligence</h2>
          <p className="font-sans text-base text-muted-foreground">Our multi-agent system mimics the workflow of a senior site reliability engineer, but operates at the speed of silicon.</p>
        </div>
        
        <div className="grid grid-cols-12 gap-6">
          {/* Feature 1: Log Parsing */}
          <motion.div 
            whileHover={{ y: -4, borderColor: "rgba(175, 198, 255, 0.3)" }}
            className="col-span-12 md:col-span-8 bg-card/70 backdrop-blur-md border border-white/10 p-10 rounded-2xl transition-all"
          >
            <div className="flex flex-col md:flex-row gap-10 items-center">
              <div className="flex-1 space-y-6">
                <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center text-primary">
                  <Terminal className="w-6 h-6" />
                </div>
                <h3 className="font-sans text-2xl font-bold text-foreground">Intelligent Log Parsing</h3>
                <p className="font-sans text-base text-muted-foreground">
                  We don't just grep. Our parser understands structured formats, identifies timestamps, correlates multi-process execution, and strips out noise to find the needle in the haystack.
                </p>
              </div>
              <div className="flex-1 w-full bg-popover rounded-xl p-4 border border-white/5 overflow-hidden shadow-inner">
                <div className="font-mono text-sm text-[#6bff8f] mb-2">$ analyzing_job_284...</div>
                <div className="font-mono text-sm text-muted-foreground opacity-60">Step 4: npm install ... [OK]</div>
                <div className="font-mono text-sm text-muted-foreground opacity-60">Step 5: npm test ...</div>
                <div className="font-mono text-sm text-destructive bg-destructive/10 px-2 rounded mt-2">Error: Connection refused (127.0.0.1:5432)</div>
                <div className="font-mono text-sm text-primary mt-2">Agent Action: Checking database container logs...</div>
              </div>
            </div>
          </motion.div>

          {/* Feature 2: AI Classification */}
          <motion.div 
            whileHover={{ y: -4, borderColor: "rgba(175, 198, 255, 0.3)" }}
            className="col-span-12 md:col-span-4 bg-card/70 backdrop-blur-md border border-white/10 p-10 rounded-2xl transition-all"
          >
            <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center text-primary mb-6">
              <Lightbulb className="w-6 h-6" />
            </div>
            <h3 className="font-sans text-2xl font-bold text-foreground mb-4">AI Classification</h3>
            <p className="font-sans text-base text-muted-foreground">
              Instantly categorize failures into Infrastructure, Network, Code, or Flaky tests using our fine-tuned proprietary models.
            </p>
          </motion.div>

          {/* Feature 3: Agentic Planning */}
          <motion.div 
            whileHover={{ y: -4, borderColor: "rgba(175, 198, 255, 0.3)" }}
            className="col-span-12 md:col-span-4 bg-card/70 backdrop-blur-md border border-white/10 p-10 rounded-2xl transition-all"
          >
            <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center text-primary mb-6">
              <Network className="w-6 h-6" />
            </div>
            <h3 className="font-sans text-2xl font-bold text-foreground mb-4">Agentic Planning</h3>
            <p className="font-sans text-base text-muted-foreground">
              Agents dynamically create a search strategy based on the initial failure signature, pivoting as new evidence is uncovered.
            </p>
          </motion.div>

          {/* Feature 4: Semantic Retrieval */}
          <motion.div 
            whileHover={{ y: -4, borderColor: "rgba(175, 198, 255, 0.3)" }}
            className="col-span-12 md:col-span-8 bg-card/70 backdrop-blur-md border border-white/10 p-10 rounded-2xl transition-all"
          >
            <div className="flex flex-col md:flex-row gap-10">
              <div className="flex-1">
                <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center text-primary mb-6">
                  <Search className="w-6 h-6" />
                </div>
                <h3 className="font-sans text-2xl font-bold text-foreground mb-4">Semantic Retrieval</h3>
                <p className="font-sans text-base text-muted-foreground">
                  Our Vector DB indexes your entire documentation, past PRs, and resolved issues to find similar patterns and historical solutions in milliseconds.
                </p>
              </div>
              <div className="flex-1 grid grid-cols-2 gap-4">
                <div className="bg-popover rounded-xl p-4 border border-white/5 flex flex-col items-center justify-center gap-2 shadow-inner">
                  <Network className="text-primary w-8 h-8" />
                  <span className="font-sans text-xs font-semibold tracking-wider uppercase text-muted-foreground mt-2">Knowledge Graph</span>
                </div>
                <div className="bg-popover rounded-xl p-4 border border-white/5 flex flex-col items-center justify-center gap-2 shadow-inner">
                  <Search className="text-secondary w-8 h-8" />
                  <span className="font-sans text-xs font-semibold tracking-wider uppercase text-muted-foreground mt-2">Embeddings</span>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  )
}

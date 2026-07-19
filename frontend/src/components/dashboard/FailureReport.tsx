import { Download, Share, BrainCircuit } from "lucide-react"
import { motion } from "framer-motion"

export default function FailureReport() {
  return (
    <div className="lg:col-span-7 space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="bg-card/60 backdrop-blur-md p-6 lg:p-8 rounded-xl border-t-2 border-t-primary-container border-x border-b border-white/10">
        
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 mb-6">
          <div>
            <span className="bg-destructive/20 text-destructive px-2 py-1 rounded font-sans text-xs font-semibold tracking-wider uppercase mb-2 inline-block">Configuration Error</span>
            <h1 className="font-sans text-3xl font-bold text-foreground">Root Cause: Environment Variable Mismatch</h1>
          </div>
          
          <div className="relative flex items-center justify-center">
            <svg className="w-24 h-24 transform -rotate-90">
              <circle className="text-border" cx="48" cy="48" fill="transparent" r="40" stroke="currentColor" strokeWidth="8"></circle>
              <circle className="text-primary transition-all duration-1000" cx="48" cy="48" fill="transparent" r="40" stroke="currentColor" strokeDasharray="251.2" strokeDashoffset="27.6" strokeLinecap="round" strokeWidth="8"></circle>
            </svg>
            <span className="absolute font-sans text-2xl font-bold text-primary">89%</span>
            <div className="absolute -bottom-6 font-sans text-xs font-semibold tracking-wider uppercase text-muted-foreground">Confidence</div>
          </div>
        </div>

        <div className="flex items-center gap-2 mb-6">
          <span className="w-2 h-2 rounded-full bg-[#4ae176] shadow-[0_0_8px_#4ae176]"></span>
          <span className="text-[#4ae176] font-sans text-xs font-semibold tracking-wider uppercase">Approved by Critic</span>
        </div>

        <div className="space-y-6">
          <section>
            <h3 className="font-sans text-xs font-semibold tracking-wider uppercase text-primary mb-2">Analysis Summary</h3>
            <p className="font-sans text-base text-muted-foreground leading-relaxed">
              The CI/CD pipeline failed during the <code className="bg-popover px-1.5 py-0.5 rounded font-mono text-sm">pre-deploy-check</code> stage. Our AI agents detected that the <code className="bg-popover px-1.5 py-0.5 rounded font-mono text-sm">DATABASE_URL</code> provided in the GitHub Secrets does not match the expected schema required by the migration script in <code className="bg-popover px-1.5 py-0.5 rounded font-mono text-sm">v2.4.1</code>. This discrepancy resulted in a 401 Unauthorized error during the connection handshake.
            </p>
          </section>

          <section>
            <h3 className="font-sans text-xs font-semibold tracking-wider uppercase text-primary mb-2">Suggested Fixes</h3>
            <div className="bg-[#05070A] border-l-4 border-primary p-4 rounded-md overflow-x-auto">
              <pre className="font-mono text-sm text-foreground"><code>{`# Update your .github/workflows/deploy.yml
- name: Verify Env
  run: |
    echo "DB_TYPE=postgres" >> $GITHUB_ENV
    # Ensure correct suffix for SSL connection
    echo "DATABASE_URL=\${{ secrets.DB_CONN }}?sslmode=require" >> $GITHUB_ENV`}</code></pre>
            </div>
            <p className="mt-4 text-sm font-sans text-muted-foreground italic">Note: Ensure your cloud provider supports the <code className="font-mono text-sm">sslmode=require</code> parameter before applying.</p>
          </section>

          <div className="flex flex-wrap gap-4 pt-6 border-t border-white/5">
            <motion.button 
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="flex items-center gap-2 bg-primary-container text-primary-foreground px-6 py-2 rounded-lg font-sans text-xs font-semibold tracking-wider uppercase"
            >
              <Download className="w-4 h-4" /> Download Report
            </motion.button>
            <motion.button 
              whileHover={{ backgroundColor: "rgba(255,255,255,0.05)" }}
              whileTap={{ scale: 0.98 }}
              className="flex items-center gap-2 border border-border text-foreground px-6 py-2 rounded-lg font-sans text-xs font-semibold tracking-wider uppercase"
            >
              <Share className="w-4 h-4" /> Export JSON
            </motion.button>
          </div>
        </div>
      </div>

      {/* Critic Panel */}
      <div className="bg-card/60 backdrop-blur-md p-6 rounded-xl border-l-4 border-l-secondary border-y border-r border-white/10">
        <div className="flex items-center gap-3 mb-4">
          <BrainCircuit className="text-secondary w-6 h-6" />
          <h3 className="font-sans text-xl font-bold text-secondary">Critic Agent Reasoning</h3>
        </div>
        <div className="space-y-4 font-sans text-sm text-muted-foreground">
          <div className="flex gap-4">
            <div className="w-1 bg-[#6001d1] rounded-full"></div>
            <div>
              <p className="font-bold text-secondary mb-1">Hallucination Check: PASSED</p>
              <p>Verified suggested fix against latest <code className="font-mono text-xs text-foreground">v2.4.1</code> documentation and matching CI logs from similar projects in our dataset.</p>
            </div>
          </div>
          <div className="flex gap-4">
            <div className="w-1 bg-[#6001d1] rounded-full"></div>
            <div>
              <p className="font-bold text-secondary mb-1">Conflict Resolution</p>
              <p>Agent initially suggested a VPC issue, but Critic corrected pathing to Environment Variables based on line 452 of the build log.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

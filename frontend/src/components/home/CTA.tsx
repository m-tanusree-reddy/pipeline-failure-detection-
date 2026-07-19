import { motion } from "framer-motion"

export default function CTA() {
  return (
    <section className="py-24">
      <div className="max-w-[1440px] mx-auto px-6">
        <motion.div 
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          className="relative overflow-hidden bg-card/70 backdrop-blur-md border border-white/10 rounded-2xl p-16 text-center flex flex-col items-center gap-6 shadow-2xl"
        >
          <div className="absolute inset-0 bg-gradient-to-tr from-primary/10 via-transparent to-secondary/10 pointer-events-none"></div>
          
          <h2 className="relative font-sans text-5xl font-bold text-foreground">Ready to fix pipelines faster?</h2>
          <p className="relative font-sans text-lg text-muted-foreground max-w-xl">
            Join 500+ engineering teams who have automated their CI failure triage. Start your 14-day free trial today.
          </p>
          
          <div className="relative flex flex-wrap justify-center gap-4 mt-4">
            <motion.button 
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="bg-primary text-primary-foreground font-bold py-4 px-10 rounded-full shadow-[0_0_20px_0_rgba(175,198,255,0.15)] transition-all text-base"
            >
              Get Started Now
            </motion.button>
            <motion.button 
              whileHover={{ backgroundColor: "rgba(255,255,255,0.05)" }}
              className="bg-[#232a3c] border border-border text-foreground font-bold py-4 px-10 rounded-full transition-all text-base"
            >
              Talk to Sales
            </motion.button>
          </div>
        </motion.div>
      </div>
    </section>
  )
}

export default function Stats() {
  return (
    <section className="border-y border-white/5 py-10 bg-[#070e1f]">
      <div className="max-w-[1440px] mx-auto px-6 grid grid-cols-2 md:grid-cols-4 gap-6">
        <div className="flex flex-col">
          <span className="font-sans text-5xl font-bold text-foreground">98%</span>
          <span className="font-sans text-xs font-semibold tracking-wider uppercase text-muted-foreground mt-2">Success Rate</span>
        </div>
        <div className="flex flex-col">
          <span className="font-sans text-5xl font-bold text-foreground">&lt;10s</span>
          <span className="font-sans text-xs font-semibold tracking-wider uppercase text-muted-foreground mt-2">Mean Time to Diagnose</span>
        </div>
        <div className="flex flex-col">
          <span className="font-sans text-5xl font-bold text-foreground">50M+</span>
          <span className="font-sans text-xs font-semibold tracking-wider uppercase text-muted-foreground mt-2">Logs Parsed</span>
        </div>
        <div className="flex flex-col">
          <span className="font-sans text-5xl font-bold text-foreground">0s</span>
          <span className="font-sans text-xs font-semibold tracking-wider uppercase text-muted-foreground mt-2">Manual Effort</span>
        </div>
      </div>
    </section>
  )
}

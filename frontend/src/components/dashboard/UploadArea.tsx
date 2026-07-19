import { UploadCloud } from "lucide-react"

interface UploadAreaProps {
  onUpload: () => void
}

export default function UploadArea({ onUpload }: UploadAreaProps) {
  return (
    <div 
      className="flex-1 flex flex-col items-center justify-center border-2 border-dashed border-border rounded-xl bg-card transition-all duration-500 group relative m-8 mt-4"
      onDragOver={(e) => { e.preventDefault(); e.currentTarget.classList.add('border-primary', 'bg-primary/5') }}
      onDragLeave={(e) => { e.currentTarget.classList.remove('border-primary', 'bg-primary/5') }}
      onDrop={(e) => { e.preventDefault(); onUpload() }}
      onClick={onUpload}
    >
      <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity rounded-xl pointer-events-none"></div>
      
      <div className="text-center z-10 p-16 flex flex-col items-center cursor-pointer">
        <div className="w-24 h-24 mb-6 rounded-full bg-popover border border-white/10 flex items-center justify-center shadow-2xl group-hover:scale-110 transition-transform duration-500">
          <UploadCloud className="text-primary w-12 h-12 animate-[pulse-soft_2s_ease-in-out_infinite]" />
        </div>
        <h2 className="font-sans text-3xl font-bold text-foreground mb-2">Drag and drop GitHub Actions log</h2>
        <p className="text-muted-foreground font-sans text-base mb-10 max-w-md mx-auto">
          Upload .txt, .zip, or .log files. Our AI engine will parse the infrastructure trail and identify the root cause of failures.
        </p>
        <div className="flex gap-4">
          <span className="px-6 py-2 bg-white/5 border border-white/10 rounded-full font-mono text-xs text-muted-foreground">.log</span>
          <span className="px-6 py-2 bg-white/5 border border-white/10 rounded-full font-mono text-xs text-muted-foreground">.txt</span>
          <span className="px-6 py-2 bg-white/5 border border-white/10 rounded-full font-mono text-xs text-muted-foreground">.zip</span>
        </div>
      </div>
      
      <style>{`
        @keyframes pulse-soft {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.7; }
        }
      `}</style>
    </div>
  )
}

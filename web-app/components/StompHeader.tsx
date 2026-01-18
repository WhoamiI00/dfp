"use client";

interface StompHeaderProps {
    title?: string;
    subtitle?: string;
    className?: string;
}

export const StompHeader = ({ title = "IVEN-TRON", subtitle = "AUTONOMOUS WAREHOUSE SOLUTIONS", className = "" }: StompHeaderProps) => {
    return (
        <div className={`relative flex flex-col items-center justify-center p-4 min-h-[50vh] ${className}`}>

            {/* Massive Stomp Title */}
            <h1 className="animate-stomp text-[12vw] sm:text-[15vw] font-black leading-none tracking-tighter text-transparent bg-clip-text bg-gradient-to-b from-white to-neutral-500 z-10 select-none drop-shadow-[0_0_50px_rgba(255,255,255,0.2)]">
                {title}
            </h1>

            {/* Cinematic Subtitle */}
            <div className="animate-slide-up stagger-5 mt-4 sm:mt-8 overflow-hidden rounded-full border border-white/10 bg-white/5 backdrop-blur-md px-6 py-2">
                <p className="text-[10px] sm:text-xs font-mono tracking-[0.3em] text-white/80 uppercase">
                    {subtitle}
                </p>
            </div>

            {/* Decorative Grid Lines */}
            <div className="absolute inset-0 z-0 pointer-events-none">
                <div className="absolute top-1/2 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-white/20 to-transparent animate-draw-line" />
                <div className="absolute left-1/2 top-0 h-full w-[1px] bg-gradient-to-b from-transparent via-white/20 to-transparent opacity-50" />
            </div>
        </div>
    );
};

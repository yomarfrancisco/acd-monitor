// Tabs
const tabs = [...document.querySelectorAll('[role="tab"]')];
const panels = [...document.querySelectorAll('[role="tabpanel"]')];

tabs.forEach(t => t.addEventListener('click', () => {
    tabs.forEach(x => x.setAttribute('aria-selected', String(x === t)));
    panels.forEach(p => p.hidden = p.id !== t.getAttribute('aria-controls'));
}));

// Simple real-time multi-series chart for CDS (bps)
const canvas = document.getElementById('heroChart');
const ctx = canvas.getContext('2d');
const DPR = Math.max(1, window.devicePixelRatio || 1);
let W, H, PAD = 28;

const series = [
    {name:'FNB', color:'#1e40af', data:[]},
    {name:'Standard Bank', color:'#0ea5e9', data:[]},
    {name:'Absa', color:'#10b981', data:[]},
    {name:'Nedbank', color:'#f59e0b', data:[]},
];

const POINTS = 540; // ~18 months daily points

function resize(){
    const cssW = canvas.clientWidth || canvas.parentElement.clientWidth;
    const cssH = 180;
    canvas.width = cssW * DPR;
    canvas.height = cssH * DPR;
    canvas.style.width = cssW + 'px';
    canvas.style.height = cssH + 'px';
    W = canvas.width;
    H = canvas.height;
    draw();
}

window.addEventListener('resize', resize);

// Seed CDS levels in bps (illustrative): 160–240 bps range with gentle noise
function seed(){
    const bases = [185, 195, 205, 200]; // FNB, Standard, Absa, Nedbank
    series.forEach((s, i) => {
        s.data = [];
        let v = bases[i];
        for(let k=0; k<POINTS; k++){
            v += (Math.random()-0.5)*1.8; // small daily drift in bps
            s.data.push(Math.round(v));
        }
    });
}

function getMinMax(){
    let min = Infinity, max = -Infinity;
    series.forEach(s => {
        s.data.forEach(v => {
            if (v<min) min=v;
            if (v>max) max=v;
        });
    });
    const pad = Math.max(5, Math.round((max-min)*0.1)); // bps padding
    return [min-pad, max+pad];
}

function xScale(i){
    return PAD*DPR + (W - 2*PAD*DPR) * (i/(POINTS-1));
}

function yScale(v, min, max){
    return H - PAD*DPR - (H - 2*PAD*DPR) * ((v - min)/(max - min));
}

function drawAxes(min, max){
    ctx.save();
    ctx.strokeStyle = '#e5e7eb';
    ctx.lineWidth = 1*DPR;
    
    // X axis
    ctx.beginPath();
    ctx.moveTo(PAD*DPR, H - PAD*DPR);
    ctx.lineTo(W - PAD*DPR, H - PAD*DPR);
    ctx.stroke();
    
    // Y labels
    ctx.fillStyle = '#64748b';
    ctx.font = `${12*DPR}px ui-sans-serif`;
    ctx.textAlign = 'right';
    ctx.textBaseline = 'middle';
    
    const steps = 4;
    for(let i=0; i<=steps; i++){
        const val = min + (i*(max-min)/steps);
        const y = yScale(val, min, max);
        ctx.fillText(Math.round(val).toString(), PAD*DPR - 6*DPR, y);
        
        // grid
        ctx.beginPath();
        ctx.moveTo(PAD*DPR, y);
        ctx.lineTo(W - PAD*DPR, y);
        ctx.strokeStyle = 'rgba(100,116,139,0.12)';
        ctx.stroke();
    }
    ctx.restore();
}

function draw(){
    const [min, max] = getMinMax();
    ctx.clearRect(0,0,W,H);
    drawAxes(min, max);
    
    series.forEach(s => {
        ctx.save();
        ctx.lineWidth = 2*DPR;
        ctx.strokeStyle = s.color;
        ctx.beginPath();
        s.data.forEach((v, i) => {
            const x = xScale(i);
            const y = yScale(v, min, max);
            if(i===0) ctx.moveTo(x,y);
            else ctx.lineTo(x,y);
        });
        ctx.stroke();
        ctx.restore();
    });
}

function tick(){
    // Simulate live updates by nudging last value and shifting window
    series.forEach(s => {
        let last = s.data[s.data.length-1];
        let nxt = last + (Math.random()-0.5)*2.0; // small move in bps
        s.data.push(Math.round(nxt));
        if(s.data.length > POINTS) s.data.shift();
    });
    draw();
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    seed();
    resize();
    setInterval(tick, 2000); // demo live update
});

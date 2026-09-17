from pathlib import Path

p = Path("frontend/react/src/features/dashboard/DashboardPage.tsx")
s = p.read_text(encoding="utf-8")
bad = 'const points=values.map((v,i)=>`${(i/Math.max(values.length-1,1))*w},${h-((v-min)/Math.max(max-min,1))*h`).join(" ");'
good = 'const points=values.map((v,i)=>`${(i/Math.max(values.length-1,1))*w},${h-((v-min)/Math.max(max-min,1))*h}`).join(" ");'
if bad not in s:
    raise SystemExit("Dashboard sparkline pattern not found")
p.write_text(s.replace(bad, good, 1), encoding="utf-8")
print("dashboard sparkline fixed")

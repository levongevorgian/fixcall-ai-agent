#!/usr/bin/env python3
"""Create an allowlisted clean archive; never package secrets or call databases."""
from pathlib import Path
import zipfile
ROOT=Path(__file__).resolve().parent
out=ROOT.parent/'FixCall_AI_Levon_Submission.zip'
allowed={'.py','.md','.json','.html','.css','.js','.yaml','.yml'}
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(ROOT.rglob('*')):
  rel=p.relative_to(ROOT)
  if not p.is_file() or any(part in {'runtime','__pycache__','.git'} for part in rel.parts):continue
  if p.name in {'.env.example','.gitignore','.dockerignore','Dockerfile'} or p.suffix in allowed:
   if p.name.startswith('.env') and p.name!='.env.example':continue
   z.write(p,'fixcall-agent/'+str(rel))
print(out)

import os
import streamlit

p = os.path.dirname(streamlit.__file__) + "/static/static/js/index.Dlja0TUX.js"
txt = open(p, "r", encoding="utf-8", errors="ignore").read()
idx = txt.find("Ff=")
if idx == -1:
    idx = txt.find("Ff =")
print("Ff definition:", txt[idx:idx + 500])

idx_pf = txt.find("Pf=")
if idx_pf == -1:
    idx_pf = txt.find("Pf =")
print("Pf definition:", txt[idx_pf:idx_pf + 500])

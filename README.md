IPT Resonator Optimization Tool
AI/ML-driven coil optimization for Wireless Power Transfer with user-friendly UX

Overview
Designing PCB-based resonators for Inductive Power Transfer (IPT) requires careful balancing of geometric parameters (trace width, spacing, turns, ratio) to achieve maximum Q-factor and efficiency.
However, traditional simulation workflows (e.g., Ansys HFSS/HFSS APIs) are:

⚠️ Time-consuming → brute force trials require huge simulation runs

⚠️ Complex → non-experts struggle with parameter tuning

⚠️ Unintuitive → engineers must manually test designs across 4D parameter space

This project introduces an AI + UX powered optimization tool that makes IPT resonator design faster, smarter, and more accessible.

 Key Features
✅ AI-driven Optimization

Latin Hypercube Sampling (LHS) for evenly distributed sampling of 4D design space
Dictionary-based Search to refine solutions near top candidates
Ranking Algorithm to identify the optimal design with maximum objective function (obj)

✅ Hardware Realism

Geometric parameters constrained by physical rules (e.g., coil inner radius ≥ 10mm)
Simulation models generated and tested directly in Ansys HFSS

✅ User Experience Layer (GUI)

Set parameter boundaries (w1, k, s, n) without coding
Define number of simulation runs per stage (coarse → fine search)
Set target frequency & constants
Automatically retrieve optimal design parameters + simulation results

Technical Architecture
 
Code Modules
utils_double.py → Links Python ↔ HFSS to build & simulate models
optimizer.py → Generates initial design database (100+ samples)
dict_search.py → Refines designs near top-ranked candidates
ranking.py (new) → Ranks all candidate designs, outputs best configuration
GUI.py → Simple interface to control runs & visualize results
Geometric Parameters
w1 → trace width (1.0 – 3.0 mm)
k → ratio between adjacent turns (1.09 – 1.115)
s → spacing between turns (2.0 – 4.0 mm)
n → number of turns (15 – 25)

Output & Results

Database of Designs → 100+ samples representing the parameter space
Refined Optimal Designs → Ranked by obj (Q-factor, efficiency)
Top 10 Candidates displayed in GUI with full geometric parameters
Example (Top 10 Ranked Designs):

index   obj     w1     k      s      n
34      0.92    2.5   1.10   3.0    22
17      0.90    1.8   1.11   2.5    19
...

 Impact
 
⏱ Reduced design iteration time from weeks → hours
📊 Improved accuracy of optimal resonator selection by 20–30% vs random search
👩‍💻 Enabled non-expert engineers to explore coil designs without learning HFSS scripting
🌱 Supports sustainable hardware R&D by reducing simulation waste


 Tech Stack
 
Python → Algorithms & HFSS integration
Ansys HFSS → Electromagnetic simulation
Pandas / JSON → Data handling & ranking
Tkinter / PyQt (GUI) → UX layer
ML Concepts → Latin Hypercube Sampling, dictionary-based refinement, ranking algorithm

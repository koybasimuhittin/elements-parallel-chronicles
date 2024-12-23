1. Compile and run using `mpiexec`:
   mpiexec -n <num_processors> python main.py input.txt output.txt
   Replace `<num_processors>` with a perfect square number + 1 (e.g., 4 + 1 = 5).

2. Input format:
   - First line: `N W T R` (Grid size, Waves, Units per faction, Rounds).
   - Subsequent lines: Unit positions for each faction per wave.

3. Output format:
   - Final grid state after all simulations, with `E`, `F`, `W`, `A` representing factions and `.` for neutral cells.

4. Notes:
   - Ensure the input grid size and number of processes align with the checkered partitioning strategy.